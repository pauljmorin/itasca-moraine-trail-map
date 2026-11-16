#!/usr/bin/env python3
"""Pull the White Earth Reservation boundary (public federal data).

Source (same source as the viewer's Leech Lake layer, 2026-11-16):
  Bureau of Indian Affairs, American Indian and Alaska Native
  Land Area Representation (AIAN-LAR) national dataset,
  FeatureServer DivLTR/BIA_AIAN_National_LAR layer 0,
  feature LARID 'LAR0051', LARNAME 'White Earth'.
  Geometry: MultiPolygon, 39 polygons, 1,337 vertices — one large
  main body (745,723 ac) plus 38 small trust parcels inside/near it.

Why BIA, not Census: same reason as Leech Lake (see
scripts/pull_leech_lake_reservation.py) — the BIA boundary is the
authoritative published federal boundary. BIA's GISACRES attribute
(1,621,000.16 ac) contradicts its own geometry by the same ~2.17x
ratio as Leech Lake's (1,794,106 vs 823,249 measured) and is NOT
used; the area below is geometry-measured (UTM 15N, 2026-11-16).

Trail inside: 19.15 mi, all LLC chapter (Connector, Foot Path),
measured 2026-11-16 against both site/data/trail-minnesota.geojson
and the chapter line site/data/trail.geojson — geodesic and UTM 15N
agree at 19.15 mi; the reservation survey
(docs/reservation-maps-survey-2026-11-16.md) independently measured
the same 19.15 mi. The largest single feature is 9.75 mi of a
9.96-mi feature. The chapter's stretches file does not cover the
LLC chapter, so no stretch name is recorded — "LLC chapter" is
the section label.

Outputs (identical GeoJSON, full unclipped geometry):
  data/native-nations/white-earth-reservation.geojson  (working)
  site/data/white-earth-reservation.geojson            (site copy)
The raw BIA fetch is kept at
  data/native-nations/bia-white-earth-lar0051.geojson

Stdlib only. Re-run to refresh: python3 scripts/pull_white_earth_reservation.py
"""
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING = os.path.join(ROOT, "data/native-nations/white-earth-reservation.geojson")
SITE = os.path.join(ROOT, "site/data/white-earth-reservation.geojson")
RAW = os.path.join(ROOT, "data/native-nations/bia-white-earth-lar0051.geojson")
BIA = ("https://biamaps.geoplatform.gov/server/rest/services/"
       "DivLTR/BIA_AIAN_National_LAR/FeatureServer/0/query")

# Measured 2026-11-16 (geodesic + UTM 15N agree) against the
# statewide NCT line and the chapter line: 19.15 mi inside, all LLC.
TRAIL_MILES_INSIDE = 19.15
TRAIL_SECTIONS_INSIDE = ["LLC chapter"]
# Geometry-measured area (UTM 15N), 2026-11-16. BIA's GISACRES
# attribute (1,621,000.16) contradicts its own geometry — not used.
AREA_ACRES = 748098
# Label point: centroid of the largest polygon, verified inside
# the BIA geometry 2026-11-16.
LABEL_LAT, LABEL_LON = 47.2276, -95.7213


def fetch():
    import urllib.parse
    q = (BIA + "?where=" + urllib.parse.quote("LARID = 'LAR0051'") +
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
    assert p["LARID"] == "LAR0051" and p["LARNAME"] == "White Earth", p
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
                "name": "White Earth Reservation",
                "band": "White Earth Nation",
                "source": "Bureau of Indian Affairs, AIAN Land Area Representation (AIAN-LAR)",
                "vintage": "AIAN-LAR national dataset (LAR0051), fetched 2026-11-16",
                "larid": "LAR0051",
                "area_acres": AREA_ACRES,
                "trail_miles_inside": TRAIL_MILES_INSIDE,
                "trail_sections_inside": TRAIL_SECTIONS_INSIDE,
                "label_lat": LABEL_LAT,
                "label_lon": LABEL_LON,
                "note": "Federal reservation boundary as published — not a legal survey.",
            },
        }],
    }
    for path in (WORKING, SITE, RAW):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(RAW, "w") as fh:
        json.dump(d, fh, separators=(",", ":"))
    for path in (WORKING, SITE):
        with open(path, "w") as fh:
            json.dump(out, fh, separators=(",", ":"))
    print(f"vertices: {verts}")
    print(f"area: {AREA_ACRES:,} acres (geometry-measured)")
    print(f"trail inside: {TRAIL_MILES_INSIDE} mi ({', '.join(TRAIL_SECTIONS_INSIDE)})")
    print(f"wrote {RAW}, {WORKING} and {SITE}")


if __name__ == "__main__":
    main()

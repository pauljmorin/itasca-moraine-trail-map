#!/bin/sh
# Build the Simple-map vector data (Paul, Nov 17, 2026).
#
# The Simple map prints black linework on white: trail, lake outlines,
# access roads, parking + trailheads, town names. Lakes, towns and
# roads come from OpenStreetMap; parking/trailheads/trail already
# live in site/data/ (gazetteer, access-points, trail).
#
# Source: Geofabrik Minnesota extract (Overpass was unreachable from
# this machine Nov 17 — main endpoint 406, kumi/private.coffee
# timeouts, nchc refused, osm.ch is Switzerland-only).
#   https://download.geofabrik.de/north-america/us/minnesota-latest.osm.pbf
#   (build used: minnesota-261116.osm.pbf, 290,781,407 bytes, Nov 16 2026)
# The 290 MB PBF is NOT committed — download it and pass its path:
#   sh scripts/build-simple-map-data.sh /tmp/minnesota-latest.osm.pbf
# Bbox is the trail corridor (trail.geojson bounds) buffered ~0.03 deg.
#
# Outputs (committed): site/data/simple-lakes.geojson,
# site/data/simple-towns.geojson, site/data/simple-roads.geojson.
set -e
PBF="${1:-/tmp/minnesota-latest.osm.pbf}"
OUT="$(dirname "$0")/../site/data"
W=-95.64; S=46.90; E=-94.22; N=47.21
ogr2ogr -f GeoJSON "$OUT/simple-lakes.geojson" "$PBF" \
  -spat $W $S $E $N multipolygons \
  -where "natural = 'water'" -select name -lco COORDINATE_PRECISION=5
ogr2ogr -f GeoJSON "$OUT/simple-towns.geojson" "$PBF" \
  -spat $W $S $E $N points \
  -where "place IN ('city','town','village','hamlet')" \
  -select name,place -lco COORDINATE_PRECISION=5
# Roads: drivable access roads only — highway=service is left out on
# purpose (6,583 of 9,694 ways in this bbox are cabin driveways and
# parking aisles; they would grey the simple map out). Re-add it to
# the list if Paul wants driveways drawn.
ogr2ogr -f GeoJSON "$OUT/simple-roads.geojson" "$PBF" \
  -spat $W $S $E $N lines \
  -where "highway IN ('motorway','trunk','primary','secondary','tertiary','unclassified','residential','track','living_street','road')" \
  -select name,highway -lco COORDINATE_PRECISION=5
for f in simple-lakes simple-towns simple-roads; do
  echo "$f: $(python3 -c "import json;print(len(json.load(open('$OUT/$f.geojson'))['features']))") features, $(wc -c < "$OUT/$f.geojson") bytes"
done

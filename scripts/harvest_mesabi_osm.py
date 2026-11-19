#!/usr/bin/env python3
"""Harvest the Mesabi Trail from OpenStreetMap via Nominatim + OSM API.

Why this exists: Overpass is unreachable from this environment (406
on every mirror), MnDOT's BIKEWAY service is WAF-blocked and
token-gated, and the trail authority publishes a PDF map only.
OSM is the only geometry-bearing source for the Mesabi Trail.

Method:
1. Tile Nominatim bounded searches for "Mesabi Trail" along the
   Grand Rapids -> Ely corridor; collect unique way IDs.
2. Fetch each way via the OSM API /way/{id}/full (XML: way + nodes)
   and build a LineString from the nodes in order, with the way's
   surface tag.
3. Write /tmp/mesabi-osm.json as a FeatureCollection for
   scripts/pull_bike_trails.py to merge.

Nominatim usage policy: max 1 request/sec — sleeps are built in.
"""
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull; contact: pauljmorin@gmail.com)"}
NOM = "https://nominatim.openstreetmap.org/search"
OSM = "https://www.openstreetmap.org/api/0.6/way/%d/full"


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get_xml(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    # Tile the corridor lon -93.6 -> -91.8 in 0.15 deg steps, lat 47.2-48.0
    way_ids = set()
    lon = -93.6
    while lon < -91.8:
        vb = "%f,48.0,%f,47.2" % (lon, lon + 0.15)
        url = NOM + "?" + urllib.parse.urlencode({
            "q": "Mesabi Trail", "format": "json", "limit": "50",
            "viewbox": vb, "bounded": "1",
        })
        try:
            res = get_json(url)
        except Exception as e:
            print("tile %.2f FAILED: %s" % (lon, e))
            lon += 0.15
            time.sleep(1.1)
            continue
        n = 0
        for r in res:
            if r.get("osm_type") == "way" and "Mesabi Trail" in (r.get("display_name") or ""):
                way_ids.add(int(r["osm_id"]))
                n += 1
        print("tile %.2f-%.2f: %d results, %d Mesabi ways (total %d)"
              % (lon, lon + 0.15, len(res), n, len(way_ids)))
        lon += 0.15
        time.sleep(1.1)

    print("unique Mesabi ways: %d" % len(way_ids))
    feats = []
    failed = []
    for i, wid in enumerate(sorted(way_ids)):
        try:
            xml = get_xml(OSM % wid)
        except Exception as e:
            failed.append((wid, str(e)))
            time.sleep(1.1)
            continue
        root = ET.fromstring(xml)
        nodes = {}
        way = None
        for el in root:
            if el.tag == "node":
                nodes[int(el.get("id"))] = (float(el.get("lon")), float(el.get("lat")))
            elif el.tag == "way":
                way = el
        if way is None:
            failed.append((wid, "no way element"))
            time.sleep(1.1)
            continue
        pts = []
        tags = {}
        for child in way:
            if child.tag == "nd":
                ref = int(child.get("ref"))
                if ref in nodes:
                    pts.append(nodes[ref])
            elif child.tag == "tag":
                tags[child.get("k")] = child.get("v")
        if len(pts) < 2:
            failed.append((wid, "fewer than 2 nodes"))
            time.sleep(1.1)
            continue
        feats.append({
            "type": "Feature",
            "properties": {
                "osm_way_id": wid,
                "surface": tags.get("surface"),
                "name": tags.get("name"),
            },
            "geometry": {"type": "LineString", "coordinates": pts},
        })
        if (i + 1) % 25 == 0:
            print("fetched %d/%d ways" % (i + 1, len(way_ids)))
        time.sleep(1.1)
    print("fetched %d ways, %d failed: %s" % (len(feats), len(failed), failed[:10]))
    with open("/tmp/mesabi-osm.json", "w") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh)
    print("wrote /tmp/mesabi-osm.json with %d features" % len(feats))


if __name__ == "__main__":
    main()

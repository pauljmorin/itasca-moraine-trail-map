#!/usr/bin/env python3
"""Seed the chapter-owned places file from the NCTA point data.

ONE-TIME seed (run once, Nov 10, 2026): every Camping feature in
data/points/ncta-points.geojson becomes a chapter entry in
data/points/chapter-places.geojson — the chapter's own copy of the
point, at the same coordinates, carrying the NCTA name verbatim
(bare codes like BP1 stay bare; real names are the chapter's to
supply, never invented here). All enrichment fields start empty.

After this seed the working file is HAND-MAINTAINED (see
docs/chapter-places-guide.md). Do NOT re-run this script over a
maintained file — it would overwrite chapter edits. It refuses to
run when the output already exists.

SUPERSEDES KEY: the NCTA point layer carries no id field, so an
NCTA point's identity is the composite key

    ncta-points:<name>@<lon>,<lat>

with the name as recorded and the coordinates at six decimals,
exactly as they stand in data/points/ncta-points.geojson (e.g.
"ncta-points:Camping@-95.561539,46.934356"). The gazetteer build
(scripts/build_gazetteer.py) recomputes the same key for every
NCTA feature and drops the ones a chapter entry supersedes, so a
place never appears twice: the chapter version replaces the NCTA
one in the Places layer and the Find index.

Entry schema (open taxonomy, like the asset inventory):
  id             stable chapter id ("cp-bp1", "cp-camping-2", ...)
  name           display name (NCTA name verbatim at seed time)
  kind           Camping / Water / Parking / Shelter / Privy / POI
  status         open / closed / seasonal / null
  description    chapter text, or null
  capacity       free text (e.g. "6 tents"), or null
  water_note     free text about water at/near the place, or null
  source         "seeded from NCTA — chapter to confirm" at seed
                 time; "chapter" once the chapter owns the record
  added          ISO date the entry entered the chapter file
  supersedes     the NCTA composite key above, or null
  photo_drive_id Drive id of a photo-pipeline photo, or null

Usage:  python3 scripts/seed_chapter_places.py
Standard library only.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data/points/ncta-points.geojson")
DST = os.path.join(ROOT, "data/points/chapter-places.geojson")
SEEDED_DATE = "2026-11-10"
SEED_SOURCE = "seeded from NCTA — chapter to confirm"


def load(rel_path):
    with open(rel_path) as f:
        return json.load(f)


def ncta_key(name, coord):
    return "ncta-points:%s@%.6f,%.6f" % (name, coord[0], coord[1])


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "place"


def main():
    if os.path.exists(DST):
        print("REFUSING to seed: %s already exists — the chapter "
              "file is hand-maintained; seeding again would "
              "overwrite chapter edits." % DST)
        return 1
    ncta = load(SRC)["features"]
    camping = [f for f in ncta
               if (f["properties"].get("type") or "") == "Camping"]
    used = {}
    entries = []
    for f in camping:
        p = f["properties"]
        coord = f["geometry"]["coordinates"]
        name = (p.get("name") or "Camping").strip()
        base = "cp-" + slug(name)
        n = used.get(base, 0) + 1
        used[base] = n
        cid = base if n == 1 else "%s-%d" % (base, n)
        entries.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": coord},
            "properties": {
                "id": cid,
                "name": name,
                "kind": "Camping",
                "status": None,
                "description": None,
                "capacity": None,
                "water_note": None,
                "source": SEED_SOURCE,
                "added": SEEDED_DATE,
                "supersedes": ncta_key(name, coord),
                "photo_drive_id": None,
            },
        })
    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Chapter places — the Itasca Moraine "
                       "Chapter's own place records (campsites "
                       "first). Chapter-owned: re-pulls of NCTA "
                       "data never overwrite this file.",
            "seeded_from": "data/points/ncta-points.geojson "
                           "(NCTA public point data, layer 1)",
            "seeded_date": SEEDED_DATE,
            "seed_rule": "every NCTA Camping point, verbatim name, "
                         "same coordinates, enrichment fields empty",
            "supersedes_key": "ncta-points:<name>@<lon>,<lat> at "
                              "six decimals — the NCTA layer has "
                              "no id field, so name+coordinates "
                              "are the point's identity",
            "maintenance": "hand-edited; see "
                           "docs/chapter-places-guide.md",
        },
        "features": entries,
    }
    with open(DST, "w") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("seeded %d chapter places -> data/points/chapter-places.geojson"
          % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())

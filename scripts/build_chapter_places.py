#!/usr/bin/env python3
"""Emit the site copy of the chapter places: site/data/chapter-places.geojson.

The working file data/points/chapter-places.geojson is the
chapter's own source of truth — hand-maintained (see
docs/chapter-places-guide.md), seeded once from the NCTA camping
points by scripts/seed_chapter_places.py. NCTA re-pulls never
touch it.

This step is a dedicated emit, mirroring how
scripts/pull_trail_alerts.py writes site/data/trail-alerts.geojson
directly: the working entries cross verbatim (id, name, kind,
status, description, capacity, water note, source, added,
supersedes, photo Drive id), enriched with the position along the
depicted chain that scripts/build_gazetteer.py computed for the
same entries (section, chainage, NCT mile, from-west/from-east,
snap distance, off-chain flag), recovered from
site/data/gazetteer.geojson by chapter id. An entry the gazetteer
does not carry keeps honest nulls and is reported.

Run AFTER scripts/build_gazetteer.py:
    python3 scripts/build_gazetteer.py
    python3 scripts/build_chapter_places.py
Standard library only.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data/points/chapter-places.geojson")
GAZ = os.path.join(ROOT, "site/data/gazetteer.geojson")
DST = os.path.join(ROOT, "site/data/chapter-places.geojson")

GEO_FIELDS = ("section", "sections", "chainage_mi", "nct_mile",
              "from_west_mi", "from_east_mi", "snap_m", "off_chain")


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    working = load(SRC)
    gaz = load(GAZ)
    twins = {}
    for f in gaz["features"]:
        p = f["properties"]
        if p.get("source") == "chapter" and p.get("place_id"):
            twins[p["place_id"]] = p

    out = []
    missing = []
    for f in working["features"]:
        p = f["properties"]
        props = dict(p)
        twin = twins.get(p.get("id"))
        if twin is None:
            missing.append(p.get("id"))
            for k in GEO_FIELDS:
                props[k] = None
        else:
            for k in GEO_FIELDS:
                props[k] = twin.get(k)
        out.append({
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": props,
        })

    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Chapter places — site copy. Source of "
                       "truth: data/points/chapter-places.geojson "
                       "(chapter-owned, hand-maintained).",
            "built_by": "scripts/build_chapter_places.py "
                        "(chainage/section from "
                        "scripts/build_gazetteer.py output)",
            "count": len(out),
        },
        "features": out,
    }
    with open(DST, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))

    print("chapter places: %d entries -> site/data/chapter-places.geojson "
          "(%0.f KB)" % (len(out), os.path.getsize(DST) / 1e3))
    if missing:
        print("WARNING — no gazetteer twin (null chainage/section): %s"
              % ", ".join(str(m) for m in missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())

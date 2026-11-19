#!/usr/bin/env python3
"""Flag timber features inside the Arrowhead reroute corridor polygon.

Paul, Nov 19, 2026: for the Arrowhead demo, timber sales BOTH past and
examined-for-future inside the 2004 reroute corridor polygon draw solid
red. The viewer keys off the `in_reroute_polygon` property this script
sets (see `timberStyle` in site/app.js).

Clip rule: a feature counts when its polygon INTERSECTS the corridor
polygon (any overlap, even partial) — the same intersects rule the
statewide file uses for its 2-mile corridor. The `region` property is
NOT the clip: 96 of the flagged features carry region "central" (Cass
County, where the corridor's western end reaches).

Re-run after any re-pull of the statewide timber file
(scripts/pull_timber_sales_statewide.py + add_timber_timing.py),
which would wipe the flag. Idempotent: clears the flag from features
that no longer intersect.

Usage: python3 scripts/add_timber_reroute_flag.py
"""
import json
from collections import Counter
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
TIMBER = ROOT / "site" / "data" / "timber-sales-minnesota.geojson"
POLYGON = ROOT / "site" / "data" / "arrowhead-reroute-polygon.geojson"


def main():
    poly = json.loads(POLYGON.read_text())
    pg = shape(poly["features"][0]["geometry"])
    data = json.loads(TIMBER.read_text())

    inside = 0
    for f in data["features"]:
        if shape(f["geometry"]).intersects(pg):
            f["properties"]["in_reroute_polygon"] = True
            inside += 1
        else:
            f["properties"].pop("in_reroute_polygon", None)

    flagged = [f for f in data["features"]
               if f["properties"].get("in_reroute_polygon")]
    print(f"total features: {len(data['features'])}")
    print(f"inside reroute corridor polygon: {len(flagged)}")
    print("by timing:",
          dict(Counter(f["properties"].get("timing") for f in flagged)))
    print("by county:",
          dict(Counter(f["properties"].get("county") for f in flagged)))
    print("by program:",
          dict(Counter(f["properties"].get("program") for f in flagged)))

    # Single-line file, as written by the pull script.
    TIMBER.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {TIMBER}")


if __name__ == "__main__":
    main()

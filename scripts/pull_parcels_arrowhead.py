#!/usr/bin/env python3
"""Pull Minnesota parcels for the Arrowhead reroute corridor.

Companion to scripts/pull_parcels_corridor.py (the Itasca Moraine
chapter's corridor parcels). Same source, same method, different
line and a different selection rule (Paul, Nov 18, 2026):

  * Source: "Parcels, Compiled from Opt-In Open Data Counties,
    Minnesota" - MnGeo feature service, layer 0 ("Open Parcels In
    Minnesota"). The Arrowhead corridor crosses five counties,
    ALL of them in the compilation (gac_open_approval true,
    verified Nov 18, 2026 from the service's metadata layer):
    Itasca, St. Louis, Lake, Aitkin, Cass. (Cook County is NOT
    crossed - the corridor's eastern end stops in Lake County -
    and no county fallback service is needed.)
  * Line: the Arrowhead gap line,
    site/buildout/data/gap-arrowhead.geojson (the NCTA-service
    line for the Grand Rapids-to-Ely gap, 152.8 mi).
  * Selection rule (Paul's reroute-polygon rule, Nov 18, 2026):
    the reroute polygon (the 2004 NPS preferred-alternative
    corridor, site/buildout/data/corridor-2004.geojson) contains
    ALL parcels shown, and NO parcel polygons are drawn along
    the bike path or the road walk. Implemented as: only line
    segments that lie INSIDE the 2004 polygon AND are not
    bike-path (surface "paved", the Mesabi Trail) or road-walk
    (surface "road") segments take part in the crossed/adjoining
    selection. The paved/road segments fall outside the polygon
    for the most part, and the surface filter excludes the rest,
    so no parcel is selected along them.
  * crossed / adjoining: exactly as in pull_parcels_corridor.py
    (line crosses/touches the parcel or passes within 1 m;
    adjoining = boundary within 3 m of a crossed parcel).
    "All parcels inside the polygon" (45,793 parcels across
    1,255 sq mi) is NOT published as a layer: it would be a
    ~22 MB file and is not a trail corridor set. The polygon
    is the container; the corridor set is the crossed +
    adjoining ring along the in-polygon foot trail, as for ITM.

Output: data/parcels/parcels-arrowhead.geojson (working data,
with each parcel's attributes exactly as published, plus
source_county, source_dataset, corridor_class). The published
file is built by scripts/build_site_data.py (map_parcel), the
same mapping as the chapter parcels: the published OWNER name
and owner mailing address from the county record are carried
(chapter ruling Nov 10, 2026 - public record); taxpayer
name/address fields are NOT carried.

PRIVACY: the output contains landowner names as published. It
is chapter WORKING-VIEW data only and must never be published
or copied into the public view except through build_site_data.py
(see DESIGN.md privacy rules).

Usage:  python3 scripts/pull_parcels_arrowhead.py
No credentials required; the service is public.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo_util import (  # noqa: E402
    bbox_of,
    bbox_overlap,
    iter_line_segments,
    iter_poly_segments,
    point_in_geometry,
    seg_seg_dist_km,
)
from pull_parcels_corridor import (  # noqa: E402
    CANDIDATE_MARGIN_KM,
    GRID_CELL_DEG,
    KM_PER_DEG_LAT,
    KM_PER_DEG_LON,
    LINE_TOLERANCE_KM,
    RING_TOLERANCE_KM,
    build_segment_index,
    grid_envelopes,
    line_crosses_parcel,
    pull_candidates,
    segments_near,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"

GAP_LINE = REPO_ROOT / "site" / "buildout" / "data" / "gap-arrowhead.geojson"
POLYGON = REPO_ROOT / "site" / "buildout" / "data" / "corridor-2004.geojson"
OUT_PATH = REPO_ROOT / "data" / "parcels" / "parcels-arrowhead.geojson"

COUNTIES = ["Itasca", "St. Louis", "Lake", "Aitkin", "Cass"]
# Surfaces that never take part in parcel selection: the Mesabi
# Trail bike path ("paved") and the road walk ("road").
EXCLUDED_SURFACES = {"paved", "road"}


def is_parcel(props):
    """True if the compiled record carries any parcel identity at
    all. The compilation also carries attribute-empty records
    (no PIN, no owner, no land class, no value - section /
    township / range all 0): water bodies and rights-of-way,
    e.g. Pokegama Lake (~22.7 sq km) and the Mississippi River
    corridor in the Grand Rapids area. Those are not parcels and
    are dropped before selection, so the lake never renders as a
    "crossed parcel" with an empty popup. (The chapter's corridor
    has no such records - its working file carries zero
    attribute-empty features - so this filter is Arrowhead-only
    and the shared pull script is untouched.)"""
    p = props or {}
    return bool(
        p.get("county_pin") or p.get("state_pin")
        or p.get("owner_name") or p.get("useclass1")
        or p.get("xuseclass1") or p.get("ownership")
    )


def main():
    config = json.loads(CONFIG_PATH.read_text())
    psrc = config["data_sources"]["parcels_mn"]

    poly_fc = json.loads(POLYGON.read_text())
    poly_geom = poly_fc["features"][0]["geometry"]
    gap_fc = json.loads(GAP_LINE.read_text())

    # In-polygon, non-excluded line segments (the foot trail inside
    # the reroute polygon) + the mileage accounting.
    trail_segments = []
    in_miles = 0.0
    out_miles = 0.0
    excluded_miles = 0.0
    for feat in gap_fc["features"]:
        props = feat.get("properties") or {}
        surface = props.get("surface")
        length = props.get("len_miles") or 0.0
        segs = list(iter_line_segments(feat.get("geometry")))
        inside = all(
            point_in_geometry(p, poly_geom) for s in segs for p in s
        )
        if surface in EXCLUDED_SURFACES:
            excluded_miles += length
            continue
        if not inside:
            out_miles += length
            continue
        in_miles += length
        trail_segments.extend(segs)
    print(f"Gap line: {in_miles:.1f} mi in-polygon foot trail; "
          f"{excluded_miles:.1f} mi bike-path/road-walk (excluded); "
          f"{out_miles:.1f} mi foot trail outside the polygon (excluded)")
    print(f"Selection segments: {len(trail_segments)}")

    seg_index, seg_bboxes = build_segment_index(trail_segments)
    xs = [p[0] for s in trail_segments for p in s]
    ys = [p[1] for s in trail_segments for p in s]
    trail_bbox = (min(xs), min(ys), max(xs), max(ys))
    envelopes = list(grid_envelopes(trail_bbox))
    print(f"Query envelopes: {len(envelopes)}")

    candidates = []
    for county in COUNTIES:
        feats = pull_candidates(
            psrc["service_root"],
            psrc["layer_id"],
            f"{psrc['county_field']}='{county}'",
            envelopes,
        )
        print(f"Candidates {county} (compiled): {len(feats)}")
        candidates.extend((f, county, psrc["name"]) for f in feats)

    # Drop attribute-empty records (water / rights-of-way) before
    # selection; see is_parcel().
    before = len(candidates)
    candidates = [(f, c, d) for (f, c, d) in candidates
                  if is_parcel(f.get("properties"))]
    print(f"Dropped {before - len(candidates)} attribute-empty "
          f"records (water / rights-of-way, not parcels)")

    crossed, rest = [], []
    for feat, county, dsname in candidates:
        geom = feat.get("geometry")
        pb = bbox_of(geom)
        if pb and line_crosses_parcel(
            trail_segments, seg_index, seg_bboxes, geom, pb
        ):
            crossed.append((feat, county, dsname))
        else:
            rest.append((feat, county, dsname))
    print(f"Crossed parcels: {len(crossed)}; remaining candidates: {len(rest)}")

    crossed_segs = []
    for feat, _, _ in crossed:
        geom = feat.get("geometry")
        crossed_segs.append((list(iter_poly_segments(geom)), bbox_of(geom)))

    pad_lon = RING_TOLERANCE_KM / KM_PER_DEG_LON
    pad_lat = RING_TOLERANCE_KM / KM_PER_DEG_LAT
    adjoining = []
    for feat, county, dsname in rest:
        geom = feat.get("geometry")
        pb = bbox_of(geom)
        if not pb:
            continue
        segs = list(iter_poly_segments(geom))
        is_adj = False
        for csegs, cbbox in crossed_segs:
            if not bbox_overlap(pb, cbbox, pad=max(pad_lon, pad_lat)):
                continue
            for a, b in segs:
                for c, d in csegs:
                    if seg_seg_dist_km(a, b, c, d) <= RING_TOLERANCE_KM:
                        is_adj = True
                        break
                if is_adj:
                    break
            if is_adj:
                break
        if is_adj:
            adjoining.append((feat, county, dsname))
    print(f"Adjoining (ring) parcels: {len(adjoining)}")

    # Completeness guard (same as the chapter pull).
    pad_lon_m = CANDIDATE_MARGIN_KM / KM_PER_DEG_LON
    pad_lat_m = CANDIDATE_MARGIN_KM / KM_PER_DEG_LAT
    outer = (
        trail_bbox[0] - pad_lon_m,
        trail_bbox[1] - pad_lat_m,
        trail_bbox[2] + pad_lon_m,
        trail_bbox[3] + pad_lat_m,
    )
    escapees = 0
    for feat, _, _ in crossed:
        pb = bbox_of(feat.get("geometry"))
        if pb and not (
            outer[0] <= pb[0] and outer[1] <= pb[1]
            and pb[2] <= outer[2] and pb[3] <= outer[3]
        ):
            escapees += 1
    if escapees:
        print(f"WARNING: {escapees} crossed parcels extend beyond the "
              "candidate margin; their outer ring neighbours may be "
              "incomplete.")

    out_features = []
    counts = {}
    for feat, county, dsname in crossed:
        props = dict(feat.get("properties") or {})
        props["source_county"] = county
        props["source_dataset"] = dsname
        props["corridor_class"] = "crossed"
        out_features.append(
            {"type": "Feature", "geometry": feat.get("geometry"),
             "properties": props}
        )
        counts[(county, "crossed")] = counts.get((county, "crossed"), 0) + 1
    for feat, county, dsname in adjoining:
        props = dict(feat.get("properties") or {})
        props["source_county"] = county
        props["source_dataset"] = dsname
        props["corridor_class"] = "adjoining"
        out_features.append(
            {"type": "Feature", "geometry": feat.get("geometry"),
             "properties": props}
        )
        counts[(county, "adjoining")] = counts.get((county, "adjoining"), 0) + 1

    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Arrowhead reroute corridor parcels: parcels the "
                       "in-polygon foot trail crosses, plus the adjoining "
                       "ring (one parcel deep)",
            "privacy": "WORKING VIEW ONLY - contains landowner names as "
                       "published; never publish (DESIGN.md privacy rules)",
            "pulled_utc_date": pulled,
            "method": (
                f"Candidates pulled through grid envelopes over the "
                f"in-polygon foot trail bbox expanded by "
                f"{CANDIDATE_MARGIN_KM} km. Selection line = the "
                f"Arrowhead gap line restricted to segments inside the "
                f"2004 reroute polygon and not bike-path (paved) or "
                f"road-walk (road) surface: {in_miles:.1f} mi. crossed = "
                f"line crosses/touches the parcel or passes within "
                f"{LINE_TOLERANCE_KM} km of its boundary; adjoining = "
                f"boundary within {RING_TOLERANCE_KM} km of a crossed "
                "parcel's boundary. Counties: "
                + ", ".join(COUNTIES)
                + " (all gac_open_approval true in the MnGeo "
                  "compilation; Cook County is not crossed by the "
                  "corridor). 45,793 parcels intersect the 2004 polygon "
                  "as a whole and are NOT published; the polygon is the "
                  "container, not the parcel set."
            ),
            "counts_by_county_and_class": {
                f"{c}|{k}": v for (c, k), v in sorted(counts.items())
            },
            "total_features": len(out_features),
            "crossed_parcels_beyond_candidate_margin": escapees,
        },
        "features": out_features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc))
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}: {len(out_features)} features")
    print("SUMMARY " + json.dumps(out_fc["metadata"]["counts_by_county_and_class"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

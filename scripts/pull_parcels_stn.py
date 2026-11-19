#!/usr/bin/env python3
"""Pull Minnesota parcels for the Star of the North trail.

Companion to scripts/pull_parcels_arrowhead.py (the Arrowhead
reroute corridor) and scripts/pull_parcels_corridor.py (the
Itasca Moraine chapter's corridor parcels). Same source, same
method, different line and a different selection rule (Paul,
Nov 18, 2026: anything done for Arrowhead and ITM gets done
for Star of the North too):

  * Source: "Parcels, Compiled from Opt-In Open Data Counties,
    Minnesota" - MnGeo feature service, layer 0 ("Open Parcels In
    Minnesota"). The Star of the North line crosses ONE county,
    Cass, which is in the compilation (gac_open_approval true,
    verified Nov 18, 2026 from the service's metadata layer),
    so no county fallback service is needed. (Hubbard, which is
    NOT in the compilation, is not crossed - the line starts at
    the MN-84 crossing, east of the Hubbard/Cass line.)
  * Line: the Star of the North selection line,
    data/segments/trail-stn.geojson, built by
    scripts/build_stn_line.py from the official NCTA line: the
    chapter's segment per NCTA's own chapter page ("from
    Minnesota 84 to Highway 6, northeast of Remer"), 26.67 mi
    clipped (25.93 mi foot path + 0.74 mi on-road connectors),
    all in Cass County. There is NO reroute polygon for Star of
    the North, so Paul's polygon rule does not apply - but the
    underlying principle does: NO parcel polygons are drawn
    along a road walk. Implemented as: only `slice_role`
    "foot" features (trail_type "Foot Path", trail_stat "NCT")
    take part in the crossed/adjoining selection; the 3
    on-road connectors (0.74 mi) are excluded.
  * crossed / adjoining: exactly as in pull_parcels_corridor.py
    (line crosses/touches the parcel or passes within 1 m;
    adjoining = boundary within 3 m of a crossed parcel).

Output: data/parcels/parcels-stn.geojson (working data, with
each parcel's attributes exactly as published, plus
source_county, source_dataset, corridor_class). The published
file is built by scripts/build_site_data.py (map_parcel, the
same mapping as the chapter parcels: the published OWNER name
and owner mailing address from the county record are carried
(chapter ruling Nov 10, 2026 - public record); taxpayer
name/address fields are NOT carried. Cass County's compiled
records carry owner_name (280 of 306 chapter Cass parcels)
and acres_deed (acres_poly is null for all Cass records, so
acres falls back to acres_deed - map_parcel already does
this); no Shape__Area acres fallback is needed, unlike
Itasca County in the Arrowhead pull.

PRIVACY: the output contains landowner names as published. It
is chapter WORKING-VIEW data only and must never be published
or copied into the public view except through build_site_data.py
(see DESIGN.md privacy rules).

Usage:  python3 scripts/pull_parcels_stn.py
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

STN_LINE = REPO_ROOT / "data" / "segments" / "trail-stn.geojson"
OUT_PATH = REPO_ROOT / "data" / "parcels" / "parcels-stn.geojson"

COUNTIES = ["Cass"]


def is_parcel(props):
    """True if the compiled record carries any parcel identity at
    all. The compilation also carries attribute-empty records
    (no PIN, no owner, no land class, no value - section /
    township / range all 0): water bodies and rights-of-way.
    Those are not parcels and are dropped before selection, so a
    lake never renders as a "crossed parcel" with an empty
    popup and never bridges the adjoining ring. (Same filter as
    the Arrowhead pull; the chapter's corridor carries zero
    attribute-empty features, so the filter is a no-op there.)"""
    p = props or {}
    # A state_pin of just the county prefix ("27021-", no PIN
    # body) is an empty stub, not an identity: the compilation
    # carries attribute-empty shell polygons (no PIN, no owner,
    # no land class, 0 acres - fabric gaps / water / rights of
    # way) whose state_pin is the bare prefix. They pass a naive
    # "state_pin is non-null" test, so the test must look for a
    # PIN body after the prefix.
    state_pin = p.get("state_pin") or ""
    pin_body = state_pin.split("-")[-1] if "-" in state_pin else state_pin
    return bool(
        p.get("county_pin") or pin_body
        or p.get("owner_name") or p.get("useclass1")
        or p.get("xuseclass1") or p.get("ownership")
    )


def main():
    config = json.loads(CONFIG_PATH.read_text())
    psrc = config["data_sources"]["parcels_mn"]

    stn_fc = json.loads(STN_LINE.read_text())

    # Foot-path segments only: the on-road connectors never take
    # part in parcel selection (no parcels along a road walk).
    trail_segments = []
    foot_miles = 0.0
    excluded_miles = 0.0
    for feat in stn_fc["features"]:
        props = feat.get("properties") or {}
        length = props.get("len_miles") or 0.0
        if props.get("slice_role") != "foot":
            excluded_miles += length
            continue
        foot_miles += length
        trail_segments.extend(iter_line_segments(feat.get("geometry")))
    print(f"STN line: {foot_miles:.2f} mi foot trail in selection; "
          f"{excluded_miles:.2f} mi on-road connectors (excluded)")
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
            "dataset": "Star of the North trail parcels: parcels the "
                       "foot trail crosses, plus the adjoining ring "
                       "(one parcel deep)",
            "privacy": "WORKING VIEW ONLY - contains landowner names as "
                       "published; never publish (DESIGN.md privacy rules)",
            "pulled_utc_date": pulled,
            "method": (
                f"Candidates pulled through grid envelopes over the "
                f"STN line bbox expanded by {CANDIDATE_MARGIN_KM} km. "
                f"Selection line = data/segments/trail-stn.geojson "
                f"({foot_miles:.2f} mi foot trail; "
                f"{excluded_miles:.2f} mi on-road connectors excluded - "
                f"no parcels along a road walk). crossed = line "
                f"crosses/touches the parcel or passes within "
                f"{LINE_TOLERANCE_KM} km of its boundary; adjoining = "
                f"boundary within {RING_TOLERANCE_KM} km of a crossed "
                f"parcel's boundary. County: Cass (gac_open_approval "
                f"true in the MnGeo compilation; verified Nov 18, 2026)."
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

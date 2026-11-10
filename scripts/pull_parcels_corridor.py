#!/usr/bin/env python3
"""Pull Minnesota parcels for the trail corridor and select the corridor set.

Sources (see config/chapter.json and SOURCES.md):
  * "Parcels, Compiled from Opt-In Open Data Counties, Minnesota" -
    MnGeo feature service (layer "Plan Parcels Open"). Covers Becker,
    Cass and Clearwater of the counties the chapter's trail crosses.
  * Hubbard County is NOT in the state compilation (gac_open_approval
    is false there); its parcels come from the county's own open-data
    service, "Hubbard County Tax Parcels".

Method (standard library + requests only):
  * Candidates: parcels are pulled through a grid of query envelopes
    covering the official trail line's bounding box, each cell expanded
    by CANDIDATE_MARGIN_KM, and deduplicated by source object id.
    Fetching is by object id with per-chunk count verification -
    offset-paged envelope queries on the state host silently truncate.
  * Corridor selection, computed locally against the official line in
    data/segments/official-line-chapter-extent.geojson:
      - crossed:   a parcel whose boundary the line crosses, or that
                   contains a line vertex, or whose boundary comes
                   within LINE_TOLERANCE_KM of the line (tolerance
                   absorbs digitising offsets between datasets).
      - adjoining: a remaining candidate whose boundary comes within
                   RING_TOLERANCE_KM of a crossed parcel's boundary
                   (shares an edge or corner, modulo the small slivers
                   the state compilation is known to carry between
                   county datasets). One ring deep, per the design.
  * Output keeps each parcel's attributes exactly as published, plus
    three added fields: source_county, source_dataset, corridor_class.

PRIVACY: the output contains landowner names as published. It is
chapter WORKING-VIEW data only and must never be published or copied
into the public view (see DESIGN.md privacy rules).

Usage:  python3 scripts/pull_parcels_corridor.py
No credentials required; both services are public.
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo_util import (  # noqa: E402
    bbox_of,
    bbox_overlap,
    iter_line_segments,
    iter_poly_segments,
    point_in_geometry,
    seg_seg_dist_km,
    seg_seg_intersect,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"

CANDIDATE_MARGIN_KM = 2.5
GRID_CELL_DEG = 0.05
LINE_TOLERANCE_KM = 0.001  # 1 m
RING_TOLERANCE_KM = 0.003  # 3 m
KM_PER_DEG_LAT = 111.195
KM_PER_DEG_LON = 75.93  # at 47 N


def get_json(url, params=None, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last_err}")


ID_CHUNK = 500


def fetch_chunk(layer_url, oid_field, ids):
    """Fetch features for one chunk of object ids; verify the count
    and split the chunk if the server returns fewer than asked.

    (On the state enterprise host, offset-paged envelope queries in
    GeoJSON form silently truncate, so all fetching is by object id
    with per-chunk count verification.)"""
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {
        "where": where,
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
        "returnGeometry": "true",
    }
    data = get_json(f"{layer_url}/query", params=params)
    feats = data.get("features", [])
    if len(feats) != len(ids):
        if len(ids) == 1:
            raise RuntimeError(f"Feature {ids[0]} could not be fetched from {layer_url}")
        mid = len(ids) // 2
        return fetch_chunk(layer_url, oid_field, ids[:mid]) + fetch_chunk(
            layer_url, oid_field, ids[mid:]
        )
    return feats


def layer_ids(layer_url, where, envelope):
    """Object ids of features matching `where` and the envelope."""
    params = {
        "where": where,
        "geometry": json.dumps({**envelope, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "json",
    }
    data = get_json(f"{layer_url}/query", params=params)
    # note: this host returns objectIds: null (not []) when nothing matches
    return data.get("objectIdFieldName", "objectid"), data.get("objectIds") or []


def grid_envelopes(trail_bbox):
    """Yield query envelopes: grid cells over the trail bbox, expanded
    by the candidate margin, keeping only cells near the trail bbox."""
    pad_lon = CANDIDATE_MARGIN_KM / KM_PER_DEG_LON
    pad_lat = CANDIDATE_MARGIN_KM / KM_PER_DEG_LAT
    min_lon, min_lat, max_lon, max_lat = trail_bbox
    lon = min_lon
    while lon < max_lon:
        lat = min_lat
        while lat < max_lat:
            yield {
                "xmin": lon - pad_lon,
                "ymin": lat - pad_lat,
                "xmax": lon + GRID_CELL_DEG + pad_lon,
                "ymax": lat + GRID_CELL_DEG + pad_lat,
            }
            lat += GRID_CELL_DEG
        lon += GRID_CELL_DEG


def pull_candidates(service_root, layer_id, where, envelopes):
    layer_url = f"{service_root.rstrip('/')}/{layer_id}"
    oid_field = None
    id_set = set()
    for env in envelopes:
        field, ids = layer_ids(layer_url, where, env)
        oid_field = oid_field or field
        id_set.update(ids)
    ids = sorted(id_set)
    feats = []
    for i in range(0, len(ids), ID_CHUNK):
        feats.extend(fetch_chunk(layer_url, oid_field, ids[i : i + ID_CHUNK]))
    return feats


GRID_INDEX_DEG = 0.02


def build_segment_index(trail_segments):
    """Grid index: cell -> indices of segments whose bbox overlaps it."""
    index = {}
    seg_bboxes = []
    for i, (a, b) in enumerate(trail_segments):
        sb = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        seg_bboxes.append(sb)
        cx0, cy0 = int(sb[0] // GRID_INDEX_DEG), int(sb[1] // GRID_INDEX_DEG)
        cx1, cy1 = int(sb[2] // GRID_INDEX_DEG), int(sb[3] // GRID_INDEX_DEG)
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                index.setdefault((cx, cy), []).append(i)
    return index, seg_bboxes


def segments_near(index, seg_bboxes, bbox):
    cx0, cy0 = int(bbox[0] // GRID_INDEX_DEG), int(bbox[1] // GRID_INDEX_DEG)
    cx1, cy1 = int(bbox[2] // GRID_INDEX_DEG), int(bbox[3] // GRID_INDEX_DEG)
    ids = set()
    for cx in range(cx0, cx1 + 1):
        for cy in range(cy0, cy1 + 1):
            ids.update(index.get((cx, cy), ()))
    return [i for i in ids if bbox_overlap(seg_bboxes[i], bbox)]


def line_crosses_parcel(trail_segments, index, seg_bboxes, parcel_geom, parcel_bbox):
    """True if the trail line crosses or touches the parcel, or passes
    within LINE_TOLERANCE_KM of its boundary."""
    for i in segments_near(index, seg_bboxes, parcel_bbox):
        a, b = trail_segments[i]
        if point_in_geometry(a, parcel_geom) or point_in_geometry(b, parcel_geom):
            return True
        hit = False
        for c, d in iter_poly_segments(parcel_geom):
            if seg_seg_intersect(a, b, c, d):
                return True
            if seg_seg_dist_km(a, b, c, d) <= LINE_TOLERANCE_KM:
                hit = True
        if hit:
            return True
    return False


def main():
    config = json.loads(CONFIG_PATH.read_text())
    psrc = config["data_sources"]["parcels_mn"]
    line_path = REPO_ROOT / config["outputs"]["official_line_chapter_extent"]
    out_path = REPO_ROOT / config["outputs"]["parcels_corridor"]

    line_fc = json.loads(line_path.read_text())
    trail_segments = []
    for feat in line_fc["features"]:
        trail_segments.extend(iter_line_segments(feat.get("geometry")))
    seg_index, seg_bboxes = build_segment_index(trail_segments)
    xs = [p[0] for s in trail_segments for p in s]
    ys = [p[1] for s in trail_segments for p in s]
    trail_bbox = (min(xs), min(ys), max(xs), max(ys))
    envelopes = list(grid_envelopes(trail_bbox))
    print(f"Trail segments: {len(trail_segments)}; query envelopes: {len(envelopes)}")

    candidates = []  # (feature, county, dataset_name)
    compiled_root = psrc["service_root"]
    compiled_layer = psrc["layer_id"]
    for county in psrc["compiled_counties_crossed_by_chapter_trail"]:
        feats = pull_candidates(
            compiled_root,
            compiled_layer,
            f"{psrc['county_field']}='{county}'",
            envelopes,
        )
        print(f"Candidates {county} (compiled): {len(feats)}")
        candidates.extend((f, county, psrc["name"]) for f in feats)

    for key, fb in psrc["fallback_county_services"].items():
        county = key.capitalize()
        feats = pull_candidates(fb["service_root"], fb["layer_id"], "1=1", envelopes)
        print(f"Candidates {county} (county service): {len(feats)}")
        candidates.extend((f, county, fb["name"]) for f in feats)

    # --- corridor selection -------------------------------------------
    crossed, rest = [], []
    for feat, county, dsname in candidates:
        geom = feat.get("geometry")
        pb = bbox_of(geom)
        if pb and line_crosses_parcel(trail_segments, seg_index, seg_bboxes, geom, pb):
            crossed.append((feat, county, dsname))
        else:
            rest.append((feat, county, dsname))
    print(f"Crossed parcels: {len(crossed)}; remaining candidates: {len(rest)}")

    crossed_segs = []  # (segments, bbox) per crossed parcel
    for feat, _, _ in crossed:
        geom = feat.get("geometry")
        crossed_segs.append((list(iter_poly_segments(geom)), bbox_of(geom)))

    pad_lon = RING_TOLERANCE_KM / KM_PER_DEG_LON
    adjoining = []
    for feat, county, dsname in rest:
        geom = feat.get("geometry")
        pb = bbox_of(geom)
        if not pb:
            continue
        segs = list(iter_poly_segments(geom))
        is_adj = False
        for csegs, cbbox in crossed_segs:
            if not bbox_overlap(pb, cbbox, pad=max(pad_lon, RING_TOLERANCE_KM / KM_PER_DEG_LAT)):
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

    # completeness guard: any crossed parcel reaching outside the
    # candidate envelope union suggests the margin was too tight
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
            outer[0] <= pb[0] and outer[1] <= pb[1] and pb[2] <= outer[2] and pb[3] <= outer[3]
        ):
            escapees += 1
    if escapees:
        print(f"WARNING: {escapees} crossed parcels extend beyond the candidate "
              "margin; their outer ring neighbours may be incomplete.")

    out_features = []
    counts = {}
    for feat, county, dsname in crossed:
        props = dict(feat.get("properties") or {})
        props["source_county"] = county
        props["source_dataset"] = dsname
        props["corridor_class"] = "crossed"
        out_features.append(
            {"type": "Feature", "geometry": feat.get("geometry"), "properties": props}
        )
        counts[(county, "crossed")] = counts.get((county, "crossed"), 0) + 1
    for feat, county, dsname in adjoining:
        props = dict(feat.get("properties") or {})
        props["source_county"] = county
        props["source_dataset"] = dsname
        props["corridor_class"] = "adjoining"
        out_features.append(
            {"type": "Feature", "geometry": feat.get("geometry"), "properties": props}
        )
        counts[(county, "adjoining")] = counts.get((county, "adjoining"), 0) + 1

    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Trail corridor parcels: parcels the official NCT line crosses, plus the adjoining ring (one parcel deep)",
            "privacy": "WORKING VIEW ONLY - contains landowner names as published; never publish (DESIGN.md privacy rules)",
            "pulled_utc_date": pulled,
            "method": (
                f"Candidates pulled through grid envelopes over the trail bbox "
                f"expanded by {CANDIDATE_MARGIN_KM} km. crossed = line crosses/touches "
                f"the parcel or passes within {LINE_TOLERANCE_KM} km of its boundary; "
                f"adjoining = boundary within {RING_TOLERANCE_KM} km of a crossed "
                "parcel's boundary (tolerance absorbs compilation slivers)."
            ),
            "counts_by_county_and_class": {
                f"{c}|{k}": v for (c, k), v in sorted(counts.items())
            },
            "total_features": len(out_features),
            "crossed_parcels_beyond_candidate_margin": escapees,
        },
        "features": out_features,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_fc))
    print(f"Wrote {out_path.relative_to(REPO_ROOT)}: {len(out_features)} features")
    print("SUMMARY " + json.dumps(out_fc["metadata"]["counts_by_county_and_class"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

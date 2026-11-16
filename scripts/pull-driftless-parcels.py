#!/usr/bin/env python3
"""Pull Iowa County (WI) parcels along the built Driftless Trail from the
Wisconsin Statewide Parcel Map Database V12 (2026), via its ArcGIS REST
service, and write data/driftless/parcels-driftless.geojson (+ viewer copy).

Service (found Nov 16, 2026 — the URL in the V11 schema doc,
Wisconsin_Statewide_Parcels, is stale/renamed; the live service is
Wisconsin_Statewide_Parcels_DB):
  https://services3.arcgis.com/n6uYoouQZW75n5WI/ArcGIS/rest/services/Wisconsin_Statewide_Parcels_DB/FeatureServer/0
Layer: V1200_WisconsinParcels_2026, 3.56M parcels, maxRecordCount 2000.

Fence (same as the Minnesota parcels layer): published county records only.
Fields kept: PARCELID, TAXPARCELID, OWNERNME1, OWNERNME2, SITEADRESS
(physical address), CONAME, GISACRES, PARCELDATE, TAXROLLYEAR, PARCELSRC.
EXCLUDED: PSTLADRESS (owner mailing address) and all value/tax fields
(CNTASSDVALUE, LNDVALUE, IMPVALUE, MFLVALUE, ESTFMKVALUE, NETPRPTA,
GRSPRPTA) — taxpayer-only fields, never published.

Buffer: 0.5 mile around the built trail lines in driftless-trail.geojson
(the three OSM segments + the traced Welsh outer loop). The planned trail
has no published geometry, so there is no planned-corridor parcel pull —
see docs/driftless-trail-2026-11-16.md.

Usage: python3 scripts/pull-driftless-parcels.py
Outputs: data/driftless/parcels-driftless.geojson and
         site/data/parcels-driftless.geojson (identical viewer copy).
"""
import json
import math
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "driftless"
SITE = REPO / "site" / "data"
TRAIL = DATA / "driftless-trail.geojson"
SERVICE = ("https://services3.arcgis.com/n6uYoouQZW75n5WI/ArcGIS/rest/services/"
           "Wisconsin_Statewide_Parcels_DB/FeatureServer/0")
HEADERS = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}
BUFFER_MI = 0.5
OUT_FIELDS = ("PARCELID,TAXPARCELID,OWNERNME1,OWNERNME2,SITEADRESS,CONAME,"
              "GISACRES,PARCELDATE,TAXROLLYEAR,PARCELSRC")
KEEP = [f.strip() for f in OUT_FIELDS.split(",")]


def query_envelope(bbox, extra_params=None):
    """Query by envelope (fast on the service); the 0.5-mi buffer filter is
    applied client-side with shapely, avoiding the service's slow
    polygon-intersection path (a polygon count query timed out at 120 s)."""
    params = {
        "where": "1=1",
        "geometry": ",".join(str(v) for v in bbox),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outSR": "4326",
        "outFields": OUT_FIELDS,
        "returnGeometry": "true",
        "f": "geojson",
    }
    if extra_params:
        params.update(extra_params)
    r = requests.get(SERVICE + "/query", params=params, headers=HEADERS, timeout=180)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"service error: {d['error']}")
    if d.get("exceededTransferLimit"):
        raise RuntimeError("query exceeded the 2000-record transfer limit")
    return d


def buffer_shape(coords, buf_m):
    """Shapely buffer (projected metres) of a lon/lat line."""
    from shapely.geometry import LineString

    lat0 = sum(c[1] for c in coords) / len(coords)
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    xy = [((lon * kx), (lat * ky)) for lon, lat in coords]
    return LineString(xy).buffer(buf_m, resolution=16), kx, ky


def main():
    trail = json.loads(TRAIL.read_text())
    feats = trail["features"]
    # One buffer polygon per feature; Taliesin features share an area, so
    # group by cluster to keep the query count low (parcels deduped by PARCELID).
    clusters = {
        "taliesin": [f for f in feats if f["properties"]["segment"] in
                     ("phoebe-point", "welsh-hills-inner", "welsh-hills-outer-loop")],
        "knobs": [f for f in feats if f["properties"]["segment"] == "knobs-road"],
    }
    seen = {}
    for cname, cfeats in clusters.items():
        # Envelope of the cluster's trail lines, expanded by the buffer.
        all_coords = [c for f in cfeats for c in f["geometry"]["coordinates"]]
        lons = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        lat0 = sum(lats) / len(lats)
        dlon = BUFFER_MI * 1609.34 / (111320.0 * math.cos(math.radians(lat0)))
        dlat = BUFFER_MI * 1609.34 / 110540.0
        bbox = (min(lons) - dlon, min(lats) - dlat,
                max(lons) + dlon, max(lats) + dlat)
        # Client-side 0.5-mi buffer shapes (projected metres).
        from shapely.geometry import shape as shp_shape
        from shapely import transform as shp_transform2
        import numpy as np
        buffers = []
        for f in cfeats:
            buf, kx, ky = buffer_shape(f["geometry"]["coordinates"],
                                       BUFFER_MI * 1609.34)
            buffers.append((buf, kx, ky))
        print(f"{cname}: envelope {tuple(round(v, 4) for v in bbox)}, "
              f"{len(cfeats)} trail feature(s)")
        gj = query_envelope(bbox)
        print(f"  envelope returned {len(gj['features'])} parcels; "
              "filtering to the 0.5-mi buffer...")
        kept = 0
        for feat in gj["features"]:
            props = {k: feat["properties"].get(k) for k in KEEP}
            pid = props.get("PARCELID") or props.get("TAXPARCELID")
            if pid in seen:
                continue
            try:
                geom = shp_shape(feat["geometry"])
            except Exception:
                continue
            inside = False
            for buf, kx, ky in buffers:
                projected = shp_transform2(
                    geom,
                    lambda c, kx=kx, ky=ky: np.column_stack([c[:, 0] * kx,
                                                             c[:, 1] * ky]))
                if projected.intersects(buf):
                    inside = True
                    break
            if not inside:
                continue
            kept += 1
            props["source"] = ("Wisconsin Statewide Parcel Map Database V12 "
                               "(2026), Iowa County, WI; pull date Nov 16, 2026")
            # County per parcel from the record itself (CONAME): the buffer
            # crosses the Wisconsin River county line, so a few parcels are
            # Sauk County even though the trail is in Iowa County.
            coname = (props.get("CONAME") or "").strip().upper()
            props["county"] = (f"{coname.title()} County, WI"
                               if coname else "Iowa County, WI")
            seen[pid] = {
                "type": "Feature",
                "properties": props,
                "geometry": feat["geometry"],
            }
        print(f"  kept {kept} parcels within the 0.5-mi buffer")
    out_feats = sorted(seen.values(),
                       key=lambda f: (f["properties"].get("PARCELID") or ""))
    print(f"TOTAL unique parcels: {len(out_feats)}")
    fc = {"type": "FeatureCollection", "features": out_feats}
    out = DATA / "parcels-driftless.geojson"
    out.write_text(json.dumps(fc))
    site_out = SITE / "parcels-driftless.geojson"
    site_out.write_text(json.dumps(fc))
    print(f"wrote {out} and {site_out} (identical)")
    # Field census for the verification note.
    owners = sum(1 for f in out_feats if f["properties"].get("OWNERNME1"))
    addrs = sum(1 for f in out_feats if f["properties"].get("SITEADRESS"))
    print(f"  with owner name: {owners}; with site address: {addrs}")
    print(f"  file bytes: {out.stat().st_size}")


if __name__ == "__main__":
    main()

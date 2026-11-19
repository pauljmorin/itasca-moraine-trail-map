#!/usr/bin/env python3
"""Pull government-owned lands for the Minnesota NCT corridor and
classify them by managing entity.

Paul, Nov 18, 2026 (voice): GO — sits NEXT TO Parcels in the panel.
Design driver (Paul): parcels give click-for-information on a piece of
ground; THIS layer tells you who the entity is you have to talk to and
work with. Categories: Federal (with kinds), State (with kinds),
Land trust, Private. Display adjustable later.

Sources (graded in docs/research-useful-layers-2026-11-11.md):
- Backbone: MnGeo "Government-Owned Lands, Derived from Opt-In Open
  Data Counties" (plan_gov_own_open/FeatureServer/0) — classes Federal /
  State / County Fee / Tax Forfeit / Tribal, inferred from parcel
  fields. Updated 2026-09-23. Covers 55 opt-in counties; Hubbard
  County is NOT in it (not opted in) — shown honestly as a gap.
- Land trust refinement: MN DNR plan_stateland_dnr, layer 1
  "Stateland Type Trust" (school/university trust land, LANDTYPE).
  Metadata 2016 — the trust polygons are PLS-forty based; they are
  used as geometry, not as a currency claim.
- State kinds: MN DNR bdry_dnr_managed_areas, layer 2 "Dnr Stat Plan
  Areas" (area_name / area_type: State Forest, State Park, State
  Recreation Area, State Wayside). §2.5's pick over bdry_state_forest.
- Federal kinds: USFS EDW ProclaimedForestBoundaries_01 layer 0
  (Chippewa + Superior National Forests, forestname) and the Tamarac
  National Wildlife Refuge boundary (local site/data/tamarac-*.geojson,
  already in the viewer).
- Tribal naming: local site/data/leech-lake-reservation.geojson and
  white-earth-reservation.geojson (already in the viewer).
- Hubbard gap fill: DNR managed-areas polygons clipped to Hubbard
  County (MnGeo bdry_counties_minnesota, co_name='Hubbard') — the
  gov-owned service has no Hubbard coverage, so the statutory
  park/forest boundary is drawn there instead, flagged gap_fill.

Corridor: the statewide NCT line (site/data/trail-minnesota.geojson,
348 features, 566.12 mi) buffered by 2 miles (3.21869 km) — the same
corridor the timber layer uses. A feature counts when its polygon
INTERSECTS the buffer (not centroid-in-buffer).

Classification (judgment register — see SOURCES.md for the full text):
  J1  Trust precedence: plan_stateland_dnr Trust polygons are drawn as
      Land trust features in their own right, and their area is
      subtracted from any gov-owned feature they overlap, so trust
      ground is drawn exactly once. Trust is a legal class (school
      trust), not a management unit, so it outranks the forest/park
      kind cut.
  J2  Kind by plurality share: a feature's kind is the overlay covering
      the largest share of its (post-trust-subtraction) corridor-clipped
      area. kind_share records that share (0-1). Features with share
      < 0.5 straddle a boundary; the plurality call stands and the
      share says so.
  J3  Private has NO geometry in this layer: the gov-owned service
      covers government land only, and deriving private ground as the
      complement would mislabel lakes, roads and other non-parcel land
      as private. Private ownership is parcel-level and already carried
      by the Parcels layer next door in the panel; the legend says so.
  J4  Hubbard gap fill uses statutory boundaries, which include private
      inholdings. Gap-fill features are flagged gap_fill=true and the
      popup says so; the Parcels layer underneath shows the inholdings.
  J5  County Fee and Tax Forfeit are carried as a County category
      (kinds: County fee / Tax-forfeit county forest land). Paul's four
      categories did not name county land, but the service returns it
      and it is a real entity to talk to; hiding it would leave holes.
      Adjustable later (hide or merge).
  J6  Tribal is carried as its own category for the same reason (the
      service returns it; the trail crosses Leech Lake Reservation).
      The nation is named by overlay with the reservation boundaries;
      features matching neither are labelled unidentified, not guessed.

Method per service: id list first (grid-envelope query for the big
services, whole-service for the small ones), then fetch by objectIds in
chunks of 500 with per-chunk count verification (repo convention — the
enterprise host silently truncates offset-paged envelope queries).
Requests with a browser UA (the enterprise host drops urllib).

Output (timber precedent — this script writes both files directly;
build_site_data.py does not rebuild them):
- data/government-owned-lands.geojson (working, full resolution)
- site/data/government-owned-lands.geojson (published, simplified 15 m,
  same tolerance as parcels)

Usage: python3 scripts/pull_gov_owned_lands.py
No credentials required; all services are public.
"""

import json
import sys
import time
from pathlib import Path

import requests
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

REPO = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}
PULLED = time.strftime("%Y-%m-%d", time.gmtime())

# Corridor: 2 miles, same as the timber layer.
BUFFER_KM = 3.21869
# Equirectangular projection at 47 N (scripts/geo_util.py convention).
KX = 75.93   # km per degree lon at 47 N
KY = 111.195  # km per degree lat
LON0, LAT0 = -93.0, 47.0
SIMPLIFY_M = 15.0  # published-file simplification, same as parcels

GOV_OWN = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
           "us_mn_state_mngeo/plan_gov_own_open/FeatureServer/0")
TRUST = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
         "us_mn_state_dnr/plan_stateland_dnr/FeatureServer/1")
MANAGED = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
           "us_mn_state_dnr/bdry_dnr_managed_areas/FeatureServer/2")
PROCLAIMED = ("https://apps.fs.usda.gov/arcx/rest/services/EDW/"
              "EDW_ProclaimedForestBoundaries_01/MapServer/0")
COUNTIES = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
            "us_mn_state_mngeo/bdry_counties_minnesota/FeatureServer/0")

GOV_FIELDS = "objectid,parcel_oid,county_pin,co_code,co_name,govt_own"
TRUST_FIELDS = "objectid,su_suid,countyname,landtype,administrator,su_acres"
MANAGED_FIELDS = "objectid,area_name,area_type,gis_acres"
PROCLAIMED_FIELDS = "objectid,forestname,gis_acres"

GRID_DEG = 0.10
ID_CHUNK = 500


def fetch_json(url, params=None, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last_err}")


def fetch_chunk(layer_url, oid_field, ids, out_fields):
    """Fetch features for one chunk of object ids; verify the count and
    split the chunk if the server returns fewer than asked."""
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {"where": where, "outFields": out_fields, "outSR": "4326",
              "f": "geojson", "returnGeometry": "true"}
    data = fetch_json(f"{layer_url}/query", params=params)
    feats = data.get("features", [])
    if len(feats) != len(ids):
        if len(ids) == 1:
            raise RuntimeError(
                f"Feature {ids[0]} could not be fetched from {layer_url}")
        mid = len(ids) // 2
        return (fetch_chunk(layer_url, oid_field, ids[:mid], out_fields)
                + fetch_chunk(layer_url, oid_field, ids[mid:], out_fields))
    return feats


def layer_ids(layer_url, where, envelope=None):
    """Object ids of features matching `where` (and the envelope)."""
    params = {"where": where, "returnIdsOnly": "true", "f": "json"}
    if envelope is not None:
        params.update({
            "geometry": json.dumps({**envelope,
                                    "spatialReference": {"wkid": 4326}}),
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
        })
    data = fetch_json(f"{layer_url}/query", params=params)
    # note: this host returns objectIds: null (not []) when nothing matches
    return data.get("objectIdFieldName", "objectid"), data.get("objectIds") or []


def pull_by_ids(layer_url, where, envelopes, out_fields):
    """Id list first (one returnIdsOnly per envelope), then fetch by
    objectIds in chunks. Envelopes may be None (whole service)."""
    oid_field = None
    id_set = set()
    envs = envelopes if envelopes is not None else [None]
    for env in envs:
        field, ids = layer_ids(layer_url, where, env)
        oid_field = oid_field or field
        id_set.update(ids)
    ids = sorted(id_set)
    feats = []
    for i in range(0, len(ids), ID_CHUNK):
        feats.extend(fetch_chunk(layer_url, oid_field, ids[i:i + ID_CHUNK],
                                 out_fields))
    return feats


# --- equirectangular helpers (47 N) ------------------------------------

def proj(lon, lat):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


def unproj(x, y):
    return (x / KX + LON0, y / KY + LAT0)


def to_km(geom):
    """GeoJSON geometry -> shapely geometry in km space."""
    from shapely.ops import transform
    return transform(lambda xs, ys: ([(x - LON0) * KX for x in xs],
                                     [(y - LAT0) * KY for y in ys]),
                     shape(geom))


def to_lonlat(geom_km):
    from shapely.ops import transform
    return transform(lambda xs, ys: ([x / KX + LON0 for x in xs],
                                     [y / KY + LAT0 for y in ys]),
                     geom_km)


def geom_to_geojson(geom_km):
    return mapping(to_lonlat(geom_km))


def line_strings(geojson_geom):
    """Yield shapely LineStrings (km space) from a GeoJSON geometry."""
    g = to_km(geojson_geom)
    if g.geom_type == "LineString":
        yield g
    elif g.geom_type == "MultiLineString":
        yield from g.geoms
    elif g.geom_type == "GeometryCollection":
        for part in g.geoms:
            if part.geom_type == "LineString":
                yield part
            elif part.geom_type == "MultiLineString":
                yield from part.geoms


def polys(geojson_geom):
    """Yield shapely Polygons (km space) from a GeoJSON geometry."""
    g = to_km(geojson_geom)
    if g.geom_type == "Polygon":
        yield g
    elif g.geom_type == "MultiPolygon":
        yield from g.geoms
    elif g.geom_type == "GeometryCollection":
        for part in g.geoms:
            if part.geom_type == "Polygon":
                yield part
            elif part.geom_type == "MultiPolygon":
                yield from part.geoms


def grid_envelopes(trail_bbox, corridor_km):
    """Yield 0.1-degree query envelopes whose box intersects the
    corridor polygon."""
    min_lon, min_lat, max_lon, max_lat = trail_bbox
    lon = min_lon
    while lon < max_lon:
        lat = min_lat
        while lat < max_lat:
            env = {"xmin": lon, "ymin": lat,
                   "xmax": lon + GRID_DEG, "ymax": lat + GRID_DEG}
            cell = shape({"type": "Polygon", "coordinates": [[
                (lon, lat), (lon + GRID_DEG, lat),
                (lon + GRID_DEG, lat + GRID_DEG), (lon, lat + GRID_DEG),
                (lon, lat)]]})
            cell_km = to_km(cell.__geo_interface__)
            if cell_km.intersects(corridor_km):
                yield env
            lat += GRID_DEG
        lon += GRID_DEG


# --- classification ------------------------------------------------------

CAT_STYLE = {}  # (filled in by the app; kept here for reference only)


def kind_for(geom_km, area_km2, overlays):
    """Plurality-share kind: the overlay covering the largest share of
    the feature's area. overlays: list of (key, shapely geom).
    Returns (key, share)."""
    best_key, best_share = None, 0.0
    for key, og in overlays:
        try:
            inter = geom_km.intersection(og)
        except Exception:  # noqa: BLE001 - topology hiccups
            continue
        if inter.is_empty:
            continue
        share = inter.area / area_km2 if area_km2 else 0.0
        if share > best_share:
            best_key, best_share = key, share
    return best_key, best_share


def main():
    t0 = time.time()
    # --- corridor -------------------------------------------------------
    trail = json.loads((REPO / "site/data/trail-minnesota.geojson").read_text())
    lines = []
    for feat in trail["features"]:
        lines.extend(line_strings(feat.get("geometry")))
    print(f"Trail line features: {len(trail['features'])}; "
          f"line parts: {len(lines)}")
    corridor_km = unary_union([ln.buffer(BUFFER_KM) for ln in lines])
    corridor_area_km2 = corridor_km.area
    print(f"Corridor area: {corridor_area_km2:.1f} km2 "
          f"({corridor_area_km2 * 247.105:.0f} ac)")
    xs = [c[0] for ln in lines for c in ln.coords]
    ys = [c[1] for ln in lines for c in ln.coords]
    # trail bbox in lon/lat for the grid (convert km coords back)
    min_lon = min(xs) / KX + LON0
    max_lon = max(xs) / KX + LON0
    min_lat = min(ys) / KY + LAT0
    max_lat = max(ys) / KY + LAT0
    envelopes = list(grid_envelopes((min_lon, min_lat, max_lon, max_lat),
                                    corridor_km))
    print(f"Query envelopes: {len(envelopes)}")

    # --- pulls ----------------------------------------------------------
    print("Pulling MnGeo government-owned lands ...")
    gov = pull_by_ids(GOV_OWN, "1=1", envelopes, GOV_FIELDS)
    print(f"  gov-owned candidates: {len(gov)}")
    print("Pulling DNR school-trust polygons ...")
    trust = pull_by_ids(TRUST, "1=1", envelopes, TRUST_FIELDS)
    print(f"  trust candidates: {len(trust)}")
    print("Pulling DNR managed areas (statutory) ...")
    managed = pull_by_ids(MANAGED, "1=1", None, MANAGED_FIELDS)
    print(f"  managed areas (statewide): {len(managed)}")
    print("Pulling USFS proclaimed forest boundaries ...")
    procl = pull_by_ids(
        PROCLAIMED, "1=1",
        [{"xmin": min_lon, "ymin": min_lat,
          "xmax": max_lon, "ymax": max_lat}], PROCLAIMED_FIELDS)
    print(f"  proclaimed forests in bbox: "
          f"{[f['properties'].get('forestname') for f in procl]}")
    print("Pulling Hubbard County boundary ...")
    hub = pull_by_ids(COUNTIES, "co_name='Hubbard'", None, "*")
    hubbard_km = None
    if hub:
        hubbard_km = unary_union(
            [p for f in hub for p in polys(f.get("geometry"))])
        print(f"  Hubbard County polygon: {hubbard_km.area:.1f} km2")

    # --- overlays -------------------------------------------------------
    trust_union = None
    trust_polys = []  # (geom, countyname) — county rides along so the
    # Land trust popup can name it (the trust source's countyname).
    for f in trust:
        cty = (f["properties"].get("countyname") or "").strip()
        for p in polys(f.get("geometry")):
            if p.intersects(corridor_km):
                trust_polys.append((p, cty))
    if trust_polys:
        trust_union = unary_union([p for p, _ in trust_polys])
    print(f"Trust polygons in corridor: {len(trust_polys)}")

    nf_overlays = []  # (forestname, geom)
    for f in procl:
        name = (f["properties"].get("forestname") or "").strip()
        if name not in ("Chippewa National Forest",
                        "Superior National Forest"):
            continue
        geoms = [p for p in polys(f.get("geometry"))
                 if p.intersects(corridor_km)]
        if geoms:
            nf_overlays.append((name, unary_union(geoms)))
    print(f"National Forest overlays: "
          f"{[(n, round(g.area, 1)) for n, g in nf_overlays]}")

    tam_paths = ["site/data/tamarac-1of3.geojson",
                 "site/data/tamarac-2of3.geojson",
                 "site/data/tamarac-3of3.geojson"]
    tam_polys = []
    for rel in tam_paths:
        d = json.loads((REPO / rel).read_text())
        for f in d["features"]:
            tam_polys.extend(polys(f.get("geometry")))
    tamarac_union = unary_union(tam_polys) if tam_polys else None
    print(f"Tamarac NWR union: "
          f"{tamarac_union.area if tamarac_union else 0:.1f} km2")

    res_overlays = []  # (nation, geom)
    for rel, nation in [("site/data/leech-lake-reservation.geojson",
                         "Leech Lake Band of Ojibwe"),
                        ("site/data/white-earth-reservation.geojson",
                         "White Earth Nation")]:
        d = json.loads((REPO / rel).read_text())
        geoms = []
        for f in d["features"]:
            geoms.extend(polys(f.get("geometry")))
        if geoms:
            res_overlays.append((nation, unary_union(geoms)))
    print(f"Reservation overlays: {[n for n, _ in res_overlays]}")

    # Managed areas intersecting the corridor, as (area_type, area_name, geom)
    managed_in = []
    for f in managed:
        props = f.get("properties") or {}
        geoms = [p for p in polys(f.get("geometry"))
                 if p.intersects(corridor_km)]
        if geoms:
            managed_in.append((props.get("area_type") or "",
                               props.get("area_name") or "",
                               unary_union(geoms)))
    print(f"Managed areas in corridor: {len(managed_in)}")
    print("  by type:", sorted(set(t for t, _, _ in managed_in)))

    # --- classify gov-owned features ------------------------------------
    out_features = []
    counts = {}
    dropped_empty = 0
    trust_subtracted = 0
    low_share = 0
    trust_by_base = {}

    def bump(cat, kind):
        counts[(cat, kind)] = counts.get((cat, kind), 0) + 1

    for feat in gov:
        props = feat.get("properties") or {}
        base = (props.get("govt_own") or "").strip()
        county = (props.get("co_name") or "").strip()
        geoms = [p for p in polys(feat.get("geometry"))]
        if not geoms:
            continue
        geom_km = unary_union(geoms).intersection(corridor_km)
        if geom_km.is_empty:
            continue
        # J1: subtract trust ground so it is drawn exactly once.
        if trust_union is not None:
            try:
                inter = geom_km.intersection(trust_union)
            except Exception:  # noqa: BLE001
                inter = None
            if inter is not None and not inter.is_empty:
                trust_subtracted += 1
                trust_by_base[base] = trust_by_base.get(base, 0) + 1
                geom_km = geom_km.difference(trust_union)
                if geom_km.is_empty:
                    dropped_empty += 1
                    continue
        area_km2 = geom_km.area
        if area_km2 <= 0:
            continue
        acres = round(area_km2 * 247.105, 1)

        if base == "Federal":
            overlays = ([(f"NF:{n}", g) for n, g in nf_overlays]
                        + ([("NWR:Tamarac", tamarac_union)]
                           if tamarac_union is not None else []))
            key, share = kind_for(geom_km, area_km2, overlays)
            if key is None:
                kind, entity = ("Other federal",
                                "Federal — managing agency not named "
                                "in this source")
                share = 0.0
            elif key.startswith("NF:"):
                fname = key[3:]
                kind = f"National Forest — {fname.replace(' National Forest', '')}"
                entity = f"USDA Forest Service — {fname}"
            else:
                kind = "National Wildlife Refuge — Tamarac"
                entity = ("U.S. Fish and Wildlife Service — "
                          "Tamarac National Wildlife Refuge")
            category = "Federal"
        elif base == "State":
            overlays = [(f"MA:{t}|{n}", g) for t, n, g in managed_in]
            key, share = kind_for(geom_km, area_km2, overlays)
            if key is None:
                kind, entity = (
                    "Other state",
                    "State of Minnesota (managing agency not "
                    "identified in this source)")
                share = 0.0
            else:
                _, rest = key.split(":", 1)
                atype, aname = rest.split("|", 1)
                if atype == "State Forest":
                    kind = f"State Forest — {aname}"
                    entity = (f"Minnesota DNR — Division of Forestry "
                              f"({aname} State Forest)")
                elif atype == "State Park":
                    kind = f"State Park — {aname}"
                    entity = (f"Minnesota DNR — Parks and Trails "
                              f"({aname} State Park)")
                elif atype == "State Recreation Area":
                    kind = f"State Recreation Area — {aname}"
                    entity = (f"Minnesota DNR — Parks and Trails "
                              f"({aname} State Recreation Area)")
                elif atype == "State Wayside":
                    kind = f"State Wayside — {aname}"
                    entity = (f"Minnesota DNR — Parks and Trails "
                              f"({aname} State Wayside)")
                else:
                    kind = f"Other state — {aname} ({atype})"
                    entity = (f"Minnesota DNR — {aname} ({atype})")
            category = "State"
        elif base in ("County Fee", "Tax Forfeit"):
            if base == "County Fee":
                kind, entity = "County fee", f"{county} County"
            else:
                kind = "Tax-forfeit (county forest land)"
                entity = f"{county} County — Tax Forfeit Land"
            category = "County"
            share = 1.0
        elif base == "Tribal":
            key, share = kind_for(geom_km, area_km2, res_overlays)
            if key is None:
                kind, entity = (
                    "Tribal (nation not identified in this source)",
                    "Tribal government (nation not identified "
                    "in this source)")
                share = 0.0
            else:
                kind = f"Tribal — {key}"
                entity = key
            category = "Tribal"
        else:
            print(f"  WARNING: unknown govt_own value {base!r} "
                  f"(pin {props.get('county_pin')}) — skipped")
            continue
        if share < 0.5 and base in ("Federal", "State", "Tribal"):
            low_share += 1
        out_features.append({
            "type": "Feature",
            "geometry": geom_to_geojson(geom_km),
            "properties": {
                "category": category,
                "kind": kind,
                "entity": entity,
                "county": county,
                "acres": acres,
                "govt_own": base,
                "county_pin": (props.get("county_pin") or None),
                "kind_share": round(share, 2),
                "source": "MnGeo Government-Owned Lands",
                "gap_fill": False,
            },
        })
        bump(category, kind)

    # --- trust polygons as Land trust features --------------------------
    # Trust ground is drawn from its own polygons (J1). Only the part
    # NOT already covered by a gov-owned feature is added here — the
    # gov-owned features above had trust subtracted, so add every trust
    # polygon clipped to the corridor, minus the gov-owned footprint is
    # unnecessary: the subtraction above already removed trust from the
    # gov-owned features, so trust polygons can be added whole.
    gov_union = None
    trust_added = 0
    for p, cty in trust_polys:
        clipped = p.intersection(corridor_km)
        if clipped.is_empty:
            continue
        trust_added += 1
        out_features.append({
            "type": "Feature",
            "geometry": geom_to_geojson(clipped),
            "properties": {
                "category": "Land trust",
                "kind": "School trust land",
                "entity": "Minnesota DNR — Lands and Minerals "
                          "(School Trust land)",
                "county": cty,
                "acres": round(clipped.area * 247.105, 1),
                "govt_own": None,
                "county_pin": None,
                "kind_share": 1.0,
                "source": "DNR plan_stateland_dnr (Stateland Type Trust)",
                "gap_fill": False,
            },
        })
        bump("Land trust", "School trust land")
    print(f"Trust features added: {trust_added}")

    # --- Hubbard gap fill ------------------------------------------------
    # J4: managed-areas polygons clipped to Hubbard County, where the
    # gov-owned service has no coverage. Statutory boundaries — they
    # include private inholdings; flagged gap_fill.
    gap_added = 0
    if hubbard_km is not None:
        for atype, aname, g in managed_in:
            clipped = g.intersection(hubbard_km).intersection(corridor_km)
            if clipped.is_empty:
                continue
            if trust_union is not None:
                clipped = clipped.difference(trust_union)
                if clipped.is_empty:
                    continue
            if atype == "State Forest":
                kind = f"State Forest — {aname}"
                entity = (f"Minnesota DNR — Division of Forestry "
                          f"({aname} State Forest)")
            elif atype == "State Park":
                kind = f"State Park — {aname}"
                entity = (f"Minnesota DNR — Parks and Trails "
                          f"({aname} State Park)")
            elif atype == "State Recreation Area":
                kind = f"State Recreation Area — {aname}"
                entity = (f"Minnesota DNR — Parks and Trails "
                          f"({aname} State Recreation Area)")
            elif atype == "State Wayside":
                kind = f"State Wayside — {aname}"
                entity = (f"Minnesota DNR — Parks and Trails "
                          f"({aname} State Wayside)")
            else:
                kind = f"Other state — {aname} ({atype})"
                entity = f"Minnesota DNR — {aname} ({atype})"
            gap_added += 1
            out_features.append({
                "type": "Feature",
                "geometry": geom_to_geojson(clipped),
                "properties": {
                    "category": "State",
                    "kind": kind,
                    "entity": entity,
                    "county": "Hubbard",
                    "acres": round(clipped.area * 247.105, 1),
                    "govt_own": "State",
                    "county_pin": None,
                    "kind_share": 1.0,
                    "source": "DNR bdry_dnr_managed_areas (statutory area)",
                    "gap_fill": True,
                },
            })
            bump("State", kind)
    print(f"Hubbard gap-fill features added: {gap_added}")

    # --- coverage stats --------------------------------------------------
    cat_acres = {}
    for f in out_features:
        p = f["properties"]
        cat_acres[p["category"]] = (cat_acres.get(p["category"], 0.0)
                                    + (p["acres"] or 0))
    print("Coverage acres by category (corridor-clipped, overlaps "
          "possible where boundaries overlap):")
    for cat in sorted(cat_acres):
        print(f"  {cat}: {cat_acres[cat]:,.0f} ac")
    print(f"Corridor total: {corridor_area_km2 * 247.105:,.0f} ac")
    print(f"Trust subtracted from gov-owned features: {trust_subtracted} "
          f"(by base class: {trust_by_base})")
    print(f"Gov-owned features dropped as fully trust: {dropped_empty}")
    print(f"Features with kind_share < 0.5: {low_share}")

    metadata = {
        "dataset": "Government-owned lands in the Minnesota NCT corridor: "
                   "who the entity is to talk to / work with (Paul, "
                   "Nov 18, 2026). Ownership-class coverage, NOT parcel "
                   "records — for a parcel's owner, see the Parcels layer.",
        "pulled_utc_date": PULLED,
        "sources": {
            "gov_owned": "MnGeo Government-Owned Lands, Derived from "
                         "Opt-In Open Data Counties "
                         "(plan_gov_own_open/FeatureServer/0), "
                         "updated 2026-09-23",
            "trust": "MN DNR plan_stateland_dnr, layer 1 Stateland Type "
                     "Trust (metadata 2016)",
            "managed_areas": "MN DNR bdry_dnr_managed_areas, layer 2 Dnr "
                             "Stat Plan Areas",
            "proclaimed_forests": "USFS EDW ProclaimedForestBoundaries_01 "
                                  "layer 0",
            "tamarac": "local site/data/tamarac-1of3/2of3/3of3.geojson "
                       "(already in the viewer)",
            "reservations": "local site/data/leech-lake-reservation.geojson "
                            "and white-earth-reservation.geojson",
            "hubbard_boundary": "MnGeo bdry_counties_minnesota "
                                "(co_name='Hubbard')",
        },
        "corridor": "site/data/trail-minnesota.geojson buffered 2 mi "
                    "(3.21869 km), same as timber",
        "counts_by_category_and_kind": {
            f"{c}|{k}": v for (c, k), v in sorted(counts.items())},
        "acres_by_category": {c: round(a, 1)
                              for c, a in sorted(cat_acres.items())},
        "corridor_acres": round(corridor_area_km2 * 247.105, 1),
        "total_features": len(out_features),
        "hubbard_gap": "Hubbard County is not in the MnGeo government-owned "
                       "service (not opted in). Managed-areas statutory "
                       "polygons clipped to Hubbard County are drawn as "
                       "gap_fill features; they include private inholdings.",
        "private_note": "Private land has NO geometry in this layer: the "
                        "gov-owned service covers government land only, "
                        "and a complement would mislabel lakes, roads and "
                        "other non-parcel land as private. Private "
                        "ownership is parcel-level — see the Parcels layer.",
        "judgments": {
            "J1_trust_precedence": "Trust polygons drawn as Land trust "
                "features; trust area subtracted from gov-owned features "
                "so trust ground is drawn once.",
            "J2_kind_by_plurality_share": "Kind = overlay covering the "
                "largest share of the feature's corridor-clipped area; "
                "kind_share records it. Share < 0.5 means the feature "
                "straddles a boundary.",
            "J3_private_no_geometry": "See private_note.",
            "J4_hubbard_statutory_boundaries": "Gap-fill features are "
                "statutory boundaries including private inholdings.",
            "J5_county_category": "County Fee / Tax Forfeit carried as a "
                "County category though Paul named four categories; "
                "adjustable later.",
            "J6_tribal_category": "Tribal carried as its own category; "
                "nation named by reservation overlay, else unidentified.",
        },
        "method": (
            "Candidates pulled by grid-envelope id queries (0.1 deg cells "
            "intersecting the corridor), fetched by objectId in chunks of "
            "500 with count verification. Clipped to the corridor by "
            "polygon intersection. Trust subtracted (J1). Kinds by "
            "plurality overlay share (J2). Hubbard gap fill (J4)."),
    }
    work_path = REPO / "data/government-owned-lands.geojson"
    work_path.parent.mkdir(parents=True, exist_ok=True)
    work_path.write_text(json.dumps(
        {"type": "FeatureCollection", "metadata": metadata,
         "features": out_features}))
    print(f"Wrote {work_path.relative_to(REPO)}: {len(out_features)} features")

    # --- published file (simplified 15 m, same as parcels) --------------
    def simplify_geom(geom_dict):
        g = to_km(geom_dict)
        s = g.simplify(SIMPLIFY_M / 1000.0, preserve_topology=True)
        if s.is_empty:
            return None
        return geom_to_geojson(s)

    pub_features = []
    dropped = 0
    for f in out_features:
        sg = simplify_geom(f["geometry"])
        if sg is None:
            dropped += 1
            continue
        pub_features.append({"type": "Feature", "geometry": sg,
                             "properties": f["properties"]})
    pub_path = REPO / "site/data/government-owned-lands.geojson"
    pub_path.write_text(json.dumps(
        {"type": "FeatureCollection", "features": pub_features},
        separators=(",", ":")))
    print(f"Wrote {pub_path.relative_to(REPO)}: {len(pub_features)} features "
          f"({dropped} dropped in simplification); "
          f"{pub_path.stat().st_size / 1e6:.2f} MB")
    print(f"Elapsed: {time.time() - t0:.0f}s")
    print("SUMMARY " + json.dumps(
        {f"{c}|{k}": v for (c, k), v in sorted(counts.items())}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

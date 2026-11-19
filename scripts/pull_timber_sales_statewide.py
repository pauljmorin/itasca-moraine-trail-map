#!/usr/bin/env python3
"""Pull timber sales STATEWIDE along the North Country Trail in Minnesota.

Paul, Nov 16, 2026: "can you do timber sales along the entire trail.
I imagine there wouldn't be any out west." — this build tests that
hypothesis with the actual numbers instead of assuming it.

Sources (all public; each feature carries its source + pull date):
- USFS EDW Activity Project Areas — Timber Sale (national service,
  Chippewa + Superior National Forests in Minnesota):
  https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_ActivityProjectAreas_01/MapServer/2
- MN DNR 10-year Stand Exam List (state-land "what's coming" polygons;
  the DNR publishes NO sold-sale polygon service — this is the
  state-land equivalent, tagged program=dnr-stand-exam-10yr):
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/biota_dnr_10yr_stand_exam_list/FeatureServer/0
- MN DNR Annual Stand Exam List (public; the year's cut of the same):
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/biota_dnr_annual_stand_exam_pub/FeatureServer/0
- County timber-sale services (same services as the chapter pulls,
  re-queried against the statewide corridor instead of the chapter bbox):
  Cass (Forestry Web Map layer 62), Hubbard (ArcGIS Online hosted),
  Becker + Clearwater (PreRX Appraisals layer 0).

Other trail counties, checked 2026-11-16 (see working/timber-statewide/
pull-log-2026-11-16.md for detail — do not re-chase these blindly):
- St. Louis County HAS a timber-sale service (LND_TimberSales folder on
  gis.stlouiscountymn.gov/server2) but the folder returns 499 Token
  Required — not publicly queryable. Do not re-probe without a token.
- Carlton County HAS timber-sale services (Active_Timber_Sales,
  Prospective_Timber_Areas) but all layers return count 0 — empty.
- Itasca County publishes no timber-sale service (enterprise host has
  only forest inventory + parcels). Lake, Cook, Wilkin, Otter Tail:
  no timber-sale GIS service found; their sales (if any) are
  auction-notice/PDF or human-route only.

Corridor: the statewide NCT line (site/data/trail-minnesota.geojson,
348 features, 566.12 mi) buffered by 2 miles (3,218.69 m) — the same
corridor the build-out viewer's motorized clip and
scripts/pull-motorized-mn-corridor.py use. A sale/stand counts when
its polygon INTERSECTS the buffer (not centroid-in-buffer).

Regions (county of the feature centroid, via TIGERweb county polygons):
- west: Wilkin, Otter Tail, Becker, Hubbard, Clearwater
  (ND border to Itasca State Park)
- central: Cass, Itasca (Chippewa NF stretch)
- arrowhead: St. Louis, Carlton, Lake, Cook (Superior NF / BRT stretch)

Output: site/data/timber-sales-minnesota.geojson — ONE file, with a
`program` field distinguishing actual sales (county-sale, usfs-edw-sale)
from planned stand exams (dnr-stand-exam-10yr, dnr-stand-exam-annual).
A stand on the exam list is NOT a sold sale (DNR's own caveat: not
every examined stand becomes a sale) — the program tag is the honesty
device. The four chapter files in site/data/logging-*.geojson are NOT
touched; their counts differ from this file's because they were clipped
to the chapter bbox (lon -95.6 to -93.9), not the 2-mile buffer.

Method per service: two-pass fetch — id list first (envelope query),
then fetch by objectIds in chunks of 500 (repo convention; the DNR
enterprise host drops urllib, so requests with a browser UA, and the
motorized script's Nov 13 note that a single envelope geometry query
silently dropped features is guarded by a returnCountOnly cross-check).

Usage: python3 scripts/pull_timber_sales_statewide.py
"""

import json
import os
import time
import urllib.parse

import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "working", "timber-statewide")
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}
PULLED = time.strftime("%Y-%m-%d", time.gmtime())

# Corridor: 2 miles, same as the build-out viewer's motorized clip.
BUFFER_KM = 3.21869
# Equirectangular projection at 47 N (scripts/geo_util.py convention).
KX = 111.320 * 0.6820  # km per degree lon at 47 N (~75.93)
KY = 111.195           # km per degree lat

EDW = ("https://apps.fs.usda.gov/arcx/rest/services/EDW/"
       "EDW_ActivityProjectAreas_01/MapServer/2")
STH = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
       "us_mn_state_dnr/biota_dnr_10yr_stand_exam_list/FeatureServer/0")
ASEL = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
        "us_mn_state_dnr/biota_dnr_annual_stand_exam_pub/FeatureServer/0")
CASS = ("https://cassweb.casscountymn.gov/arcgis/rest/services/"
        "Forestry_ForestPlan_Base/MapServer/62")
HUBBARD_SOLD = ("https://services.arcgis.com/auNjCUvKlkSqV04X/ArcGIS/rest/"
                "services/Hubbard_County_Timber_Sales/FeatureServer/0")
HUBBARD_UP = ("https://services.arcgis.com/auNjCUvKlkSqV04X/ArcGIS/rest/"
              "services/Hubbard_County_Timber_Sales/FeatureServer/1")
BECKER = ("https://gis-server.co.becker.mn.us/arcgis/rest/services/"
          "Forestry/PreRX_Appraisals/FeatureServer/0")
CLEARWATER = ("https://map.co.clearwater.mn.us/arcgis/rest/services/"
              "Forestry/PreRX_Appraisals/FeatureServer/0")

WEST = {"Wilkin", "Otter Tail", "Becker", "Hubbard", "Clearwater"}
CENTRAL = {"Cass", "Itasca"}
ARROWHEAD = {"St. Louis", "Carlton", "Lake", "Cook"}


def fetch_json(url, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("GET %s failed after %d tries: %s"
                       % (url, retries, last_err))


def to_km_geom(geom):
    """Lon/lat shapely geom -> km equirectangular geom (for buffering)."""
    from shapely.ops import transform as _t
    return _t(lambda x, y: (x * KX, y * KY), geom)


def to_lonlat_geom(geom):
    from shapely.ops import transform as _t
    return _t(lambda x, y: (x / KX, y / KY), geom)


def build_corridor():
    trail = json.load(open(os.path.join(REPO, "site", "data",
                                        "trail-minnesota.geojson")))
    lines = [shape(f["geometry"]) for f in trail["features"]]
    union = unary_union(lines)
    corridor_km = to_km_geom(union).buffer(BUFFER_KM)
    corridor = to_lonlat_geom(corridor_km)
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "corridor-2mi.geojson"), "w") as fh:
        json.dump({"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"buffer_km": BUFFER_KM},
             "geometry": mapping(corridor)}]}, fh)
    return corridor


def arcgis_rings_to_geom(rings):
    """ArcGIS polygon rings -> shapely Polygon/MultiPolygon.
    First ring is the shell, the rest are holes; repair if invalid."""
    if not rings:
        return None
    from shapely.geometry import Polygon, MultiPolygon
    polys = []
    # ArcGIS serves one polygon per feature here (rings = shell + holes),
    # but be safe: group rings by containment via polygonize fallback.
    try:
        shell = [(c[0], c[1]) for c in rings[0]]
        holes = [[(c[0], c[1]) for c in r] for r in rings[1:]]
        poly = Polygon(shell, holes)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return None
        return poly
    except Exception:
        return None


def arcgis_geom_to_shapely(g):
    if not g:
        return None
    if "rings" in g:
        return arcgis_rings_to_geom(g["rings"])
    return None


def query_ids(base, envelope):
    """Id list for features intersecting the envelope + a count check."""
    env = {"xmin": envelope[0], "ymin": envelope[1],
           "xmax": envelope[2], "ymax": envelope[3],
           "spatialReference": {"wkid": 4326}}
    params = {"where": "1=1", "geometry": json.dumps(env),
              "geometryType": "esriGeometryEnvelope",
              "spatialRel": "esriSpatialRelIntersects",
              "returnIdsOnly": "true", "f": "json"}
    url = base + "/query?" + urllib.parse.urlencode(params)
    ids = fetch_json(url).get("objectIds", [])
    params2 = dict(params)
    params2["returnIdsOnly"] = "false"
    params2["returnCountOnly"] = "true"
    url2 = base + "/query?" + urllib.parse.urlencode(params2)
    count = fetch_json(url2).get("count")
    return ids, count


def query_by_ids(base, ids, fields, oid_field="objectid"):
    out = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {"objectIds": ",".join(str(x) for x in chunk),
                  "outFields": ",".join(fields),
                  "outSR": "4326", "returnGeometry": "true", "f": "json"}
        url = base + "/query?" + urllib.parse.urlencode(params)
        out.extend(fetch_json(url).get("features", []))
    return out


def main():
    corridor = build_corridor()
    env = corridor.bounds  # (minx, miny, maxx, maxy)
    print("corridor envelope: lon %.4f..%.4f lat %.4f..%.4f"
          % (env[0], env[2], env[1], env[3]))

    counties = json.load(open(os.path.join(WORK, "mn-counties.geojson")))
    county_geoms = [(f["properties"]["NAME"].replace(" County", ""),
                     shape(f["geometry"])) for f in counties["features"]]

    def county_of(geom):
        c = geom.centroid
        for name, g in county_geoms:
            if g.contains(c):
                return name
        return None

    def region_of(county):
        if county in WEST:
            return "west"
        if county in CENTRAL:
            return "central"
        if county in ARROWHEAD:
            return "arrowhead"
        return "other"

    jobs = [
        ("edw", EDW, ["objectid", "cn", "id", "name", "projecttype",
                       "rev_date", "sale_category", "fy_award",
                       "admin_forest_name", "admin_district_name",
                       "gis_acres"], "objectid"),
        ("sth", STH, ["objectid_1", "stand_key", "se_year", "prescrip",
                       "t_acres", "stand_acre", "county", "sfrmp_name",
                       "admin", "status", "for_type", "location",
                       "survey_yr"], "objectid_1"),
        ("asel", ASEL, ["objectid", "area_desc", "plan_year",
                         "pres_prelim_code", "pres_prelim_desc",
                         "gis_acres", "stand_location", "deferred_year",
                         "sfrmp_description",
                         "planned_ctype_description"], "objectid"),
        ("cass", CASS, ["OBJECTID", "YEAR_", "POLY_NUM", "ACRES", "GIS_ID",
                         "AppraisalID", "PERMITNUM"], "OBJECTID"),
        ("hubbard-sold", HUBBARD_SOLD, ["OBJECTID", "Sale_Number",
                                         "Operator"], "OBJECTID"),
        ("hubbard-upcoming", HUBBARD_UP, ["OBJECTID", "Appraisal_ID"],
         "OBJECTID"),
        ("becker", BECKER, ["OBJECTID", "Year", "BlockNumber", "Acres",
                             "AppraisalName", "PermitNumber", "Closed",
                             "Shape__Area", "GlobalID"], "OBJECTID"),
        ("clearwater", CLEARWATER, ["OBJECTID", "Year", "BlockNumber",
                                     "Acres", "AppraisalName",
                                     "PermitNumber", "Closed",
                                     "Shape__Area", "GlobalID"],
         "OBJECTID"),
    ]

    raw = {}
    for label, base, fields, oid in jobs:
        ids, count = query_ids(base, env)
        print("%s: %d ids (count query: %s)" % (label, len(ids), count))
        feats = query_by_ids(base, ids, fields, oid)
        print("  fetched %d features" % len(feats))
        raw[label] = feats
        with open(os.path.join(WORK, "raw-%s.json" % label), "w") as fh:
            json.dump(feats, fh)

    # --- normalize + clip -------------------------------------------
    out_feats = []
    skipped = {"no_geometry": 0, "outside_corridor": 0, "invalid": 0}

    def add(props, geom):
        if geom is None or geom.is_empty:
            skipped["no_geometry"] += 1
            return
        if not geom.intersects(corridor):
            skipped["outside_corridor"] += 1
            return
        county = county_of(geom)
        props["county"] = county
        props["region"] = region_of(county)
        out_feats.append({"type": "Feature", "properties": props,
                          "geometry": mapping(geom)})

    def acres_from_sqft(sqft):
        return round(sqft / 43560.0, 1) if sqft else None

    for f in raw["edw"]:
        a = f.get("attributes") or {}
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        rev = a.get("rev_date")
        rev = (time.strftime("%Y-%m-%d", time.gmtime(rev / 1000))
               if rev else None)
        add({"program": "usfs-edw-sale",
             "manager": "USFS",
             "name": a.get("name") or ("Timber sale " + str(a.get("id"))),
             "permit": str(a.get("id")) if a.get("id") else None,
             "acres": round(a["gis_acres"], 1) if a.get("gis_acres") else None,
             "year": a.get("fy_award"),
             "rev_date": rev,
             "sale_category": a.get("sale_category"),
             "forest": a.get("admin_forest_name"),
             "district": a.get("admin_district_name"),
             "source": ("USFS EDW Activity Project Areas — Timber Sale "
                        "(pulled %s)" % PULLED)}, g)

    # STH prescrip is a bare integer code with NO coded-value domain in
    # the service. Decoded from the ASEL service's pres_prelim_code ->
    # pres_prelim_desc values (same code system, verified across 2,508
    # ASEL features: 1111/1300/1810 map 1:1 to the three descriptions).
    PRESCRIP_DESC = {1111: "Clearcut with Reserves",
                     1300: "Uneven-Aged Regen Harvest",
                     1810: "Non-Regen Harvest"}
    for f in raw["sth"]:
        a = f.get("attributes") or {}
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        add({"program": "dnr-stand-exam-10yr",
             "manager": "MN DNR",
             "name": ("Stand %s (%s)" % (a.get("stand_key"),
                                          a.get("location"))
                      if a.get("stand_key") else "DNR stand exam"),
             "permit": str(a["stand_key"]) if a.get("stand_key") else None,
             "acres": a.get("t_acres") or a.get("stand_acre"),
             "year": a.get("se_year"),
             "se_year": a.get("se_year"),
             "prescrip": a.get("prescrip"),
             "prescrip_desc": PRESCRIP_DESC.get(a.get("prescrip")),
             "sfrmp": a.get("sfrmp_name"),
             "admin": a.get("admin"),
             "status": a.get("status"),
             "source": ("MN DNR 10-year Stand Exam List, enterprise GIS "
                        "service (pulled %s); exam year + preliminary "
                        "prescription — NOT a sold sale" % PULLED)}, g)

    for f in raw["asel"]:
        a = f.get("attributes") or {}
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        add({"program": "dnr-stand-exam-annual",
             "manager": "MN DNR",
             "name": ("Stand %s (%s)" % (a.get("stand_key"),
                                          a.get("stand_location"))
                      if a.get("stand_key") else "DNR annual stand exam"),
             "permit": str(a["stand_key"]) if a.get("stand_key") else None,
             "acres": round(a["gis_acres"], 1) if a.get("gis_acres") else None,
             "year": a.get("plan_year"),
             "plan_year": a.get("plan_year"),
             "pres_prelim": a.get("pres_prelim_desc"),
             "area": a.get("area_desc"),
             "deferred_year": a.get("deferred_year"),
             "source": ("MN DNR Annual Stand Exam List (public), "
                        "enterprise GIS service (pulled %s); planned exam "
                        "— NOT a sold sale" % PULLED)}, g)

    for f in raw["cass"]:
        a = f.get("attributes") or {}
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        add({"program": "county-sale",
             "manager": "Cass County",
             "name": "Timber sale %s" % (a.get("PERMITNUM") or a.get("GIS_ID")),
             "permit": a.get("PERMITNUM"),
             "acres": a.get("ACRES"),
             "year": a.get("YEAR_"),
             "gis_id": a.get("GIS_ID"),
             "poly_num": a.get("POLY_NUM"),
             "source": ("Cass County Forestry Web Map — Timber Sales "
                        "(Current), layer 62 (pulled %s)" % PULLED)}, g)

    for f in raw["hubbard-sold"]:
        a = f.get("attributes") or {}
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        add({"program": "county-sale",
             "manager": "Hubbard County",
             "name": "Timber sale %s" % a.get("Sale_Number"),
             "permit": a.get("Sale_Number"),
             "acres": None,  # Shape__Area not requested; see note below
             "year": (2000 + int(str(a["Sale_Number"]).split("-")[0])
                      if a.get("Sale_Number") and
                      str(a["Sale_Number"]).split("-")[0].isdigit() else None),
             "status": "sold",
             "operator": a.get("Operator"),
             "source": ("Hubbard County Timber Sales (ArcGIS Online) — "
                        "Timber sales, layer 0 (pulled %s); year from "
                        "Sale_Number YY-NN prefix" % PULLED)}, g)

    for f in raw["hubbard-upcoming"]:
        a = f.get("attributes") or {}
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        add({"program": "county-sale",
             "manager": "Hubbard County",
             "name": "Timber sale %s (upcoming)" % a.get("Appraisal_ID"),
             "permit": a.get("Appraisal_ID"),
             "acres": None,
             "year": 2026,
             "status": "upcoming",
             "source": ("Hubbard County Timber Sales (ArcGIS Online) — "
                        "Upcoming Timber Sales, layer 1 (pulled %s)"
                        % PULLED)}, g)

    for label, manager in (("becker", "Becker County"),
                           ("clearwater", "Clearwater County")):
        for f in raw[label]:
            a = f.get("attributes") or {}
            g = arcgis_geom_to_shapely(f.get("geometry") or {})
            year = a.get("Year")
            if year in (None, "TBD"):
                pn = str(a.get("PermitNumber") or "")
                year = (2000 + int(pn.split("-")[0])
                        if pn.split("-")[0].isdigit() else None)
            else:
                try:
                    year = int(year)
                except (TypeError, ValueError):
                    year = None
            add({"program": "county-sale",
                 "manager": manager,
                 "name": ("Timber sale %s" % a.get("PermitNumber")
                          if a.get("PermitNumber") else
                          "Timber appraisal %s" % a.get("AppraisalName")),
                 "permit": a.get("PermitNumber"),
                 "acres": (a.get("Acres") if a.get("Acres") else
                           acres_from_sqft(a.get("Shape__Area"))),
                 "year": year,
                 "closed": a.get("Closed"),
                 "gis_id": a.get("GlobalID"),
                 "source": ("%s Forestry PreRX Appraisals, layer 0 "
                            "(pulled %s)" % (manager, PULLED))}, g)

    # Hubbard acres: Shape__Area was not in the field list; recompute
    # from geometry (equirectangular km^2 -> acres) for Hubbard features.
    for feat in out_feats:
        if feat["properties"]["manager"] == "Hubbard County":
            g = shape(feat["geometry"])
            gkm = to_km_geom(g)
            feat["properties"]["acres"] = round(gkm.area * 247.105, 1)

    from collections import Counter
    by_program = Counter(f["properties"]["program"] for f in out_feats)
    by_region = Counter(f["properties"]["region"] for f in out_feats)
    by_county = Counter(f["properties"]["county"] for f in out_feats)
    total_acres = sum((f["properties"]["acres"] or 0) for f in out_feats)
    xs, ys = [], []
    for feat in out_feats:
        g = shape(feat["geometry"])
        b = g.bounds
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]

    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("Timber sales + DNR stand exams along the full "
                        "Minnesota North Country Trail — 2-mile corridor"),
            "corridor": ("Statewide NCT line (site/data/trail-minnesota."
                         "geojson, 348 features, 566.12 mi) buffered 2 mi "
                         "(3,218.69 m); a feature counts when its polygon "
                         "intersects the buffer"),
            "programs": {
                "county-sale": "Sold/appraised county timber sales "
                               "(Cass, Hubbard, Becker, Clearwater)",
                "usfs-edw-sale": "USFS EDW timber-sale project areas "
                                 "(Chippewa + Superior NF)",
                "dnr-stand-exam-10yr": "MN DNR 10-year stand exam list — "
                    "stands planned for examination, NOT sold sales",
                "dnr-stand-exam-annual": "MN DNR annual stand exam list — "
                    "this year's cut of the same, NOT sold sales",
            },
            "regions": {
                "west": "Wilkin, Otter Tail, Becker, Hubbard, Clearwater "
                        "(ND border to Itasca State Park)",
                "central": "Cass, Itasca (Chippewa NF stretch)",
                "arrowhead": "St. Louis, Carlton, Lake, Cook "
                             "(Superior NF / Border Route stretch)",
            },
            "pulled_utc_date": PULLED,
            "features_total": len(out_feats),
            "features_by_program": dict(by_program),
            "features_by_region": dict(by_region),
            "features_by_county": dict(by_county),
            "total_acres": round(total_acres, 1),
            "skipped": skipped,
            "extent_lon": [round(min(xs), 4), round(max(xs), 4)],
            "extent_lat": [round(min(ys), 4), round(max(ys), 4)],
            "note": ("County files in site/data/logging-*.geojson are "
                     "untouched; their counts differ because they were "
                     "clipped to the chapter bbox (lon -95.6 to -93.9), "
                     "not the 2-mile buffer. DNR actual-sale polygons do "
                     "not exist as a service; the DNR timber-sale calendar "
                     "notices (PDFs with GPS points) are the actual-sales "
                     "channel and are NOT in this file."),
        },
        "features": out_feats,
    }
    out_path = os.path.join(REPO, "site", "data",
                            "timber-sales-minnesota.geojson")
    with open(out_path, "w") as fh:
        json.dump(doc, fh)
    print("WROTE %s: %d features, %.1f ac" % (out_path, len(out_feats),
                                              total_acres))
    print("by program:", dict(by_program))
    print("by region:", dict(by_region))
    print("by county:", dict(by_county))
    print("skipped:", skipped)
    print("extent lon %.4f..%.4f lat %.4f..%.4f"
          % (min(xs), max(xs), min(ys), max(ys)))


if __name__ == "__main__":
    main()

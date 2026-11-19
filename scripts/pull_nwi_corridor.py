#!/usr/bin/env python3
"""Pull NWI wetlands along the full Minnesota North Country Trail and
classify them for trail routing (GO / MAYBE / NO-GO).

Paul, Nov 18, 2026 (voice, GO): wire NWI wetlands + SSURGO soils into the
main viewer, classified per the Nov 18 classification sweep
(~/workspace/research_notes/nwi-wetland-trail-classification-20261118-1744/report.md).
This script is the wetlands half; the soils half is
scripts/pull_ssurgo_corridor.py.

SOURCE — substitutions, documented (do not re-chase blindly):
- The task brief named https://www.fws.gov/wetlands/arcgis/rest/services/Wetlands/MapServer
  — that URL now returns 404; the FWS NWI service moved to ArcGIS Online.
- The Minnesota DNR's own updated-NWI service
  (enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_wetlands_nwi/MapServer)
  returns 499 Token Required — not publicly queryable.
- This pull therefore uses the FWS national NWI as republished on ArcGIS
  Online: https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/USA_Wetlands/FeatureServer/0
  (verified live 2026-11-18). Minnesota's content in the national file is
  the DNR June 2019 update (spring-2011 leaf-off imagery + LiDAR), which
  the DNR delivered to FWS — the research report's M.1 requirement.
  Per-polygon vintage is NOT exposed by this service, so it cannot be
  verified polygon by polygon; recorded as a limit in the metadata and
  SOURCES.md. Consistency check that the served data is the updated file
  (not the 1980s file): dense small polygons (sampled min 856 m2,
  median ~7,300 m2) with forested/shrub types present in quantity — the
  1980s file missed forested/drier wetlands and had a 1-3 ac minimum.
- The report's R4b citation (Wetlands_RLIS FeatureServer) is NOT the
  national NWI — it is Portland Metro RLIS (Oregon State Plane North,
  wkid 2913); it returns 0 features in Minnesota. Do not use it.

CORRIDOR: the statewide NCT line (site/data/trail-minnesota.geojson,
348 features) buffered by 2 miles (3,218.69 m) — the same corridor as
the timber layer (scripts/pull_timber_sales_statewide.py) and the
motorized clip. A wetland counts when its polygon INTERSECTS the buffer.

METHOD: tile the corridor into 0.25-degree cells; per cell, POST a
query whose geometry is the cell's intersection with the corridor
buffer (simplified, then widened 0.5 km so the query is a superset —
the exact clip happens in Python), with resultOffset pagination
(1,000/page, orderByFields=OBJECTID). Dedupe OBJECTIDs across cells.
Why not the id-list approach (first attempt, 2026-11-18): the 56
cells hold 408,155 envelope OBJECTIDs, and fetching by 500-id IN
lists fails with HTTP 404 — the URL is too long for this service.
The geometry query also fetches only corridor-intersecting features
instead of every wetland in the cell squares. inSR=4326 is REQUIRED
on this service — envelope queries without it fail with 400.
Do NOT use the county wetlands.zip (46.4 MB, 2017 vintage) — the
Nov 11 useful-layers doc flags it STALE.

CLASSIFICATION (rules W1-W10 / C1-C4 from the Nov 18 report; the full
rule text lives in the report's Interpretation Method — this script
implements it, it does not re-derive it):
- GO is the ABSENCE of a polygon (W1) — there is nothing to draw, so
  no GO features exist in this file.
- Riverine first (W8; the §6 table row takes precedence for System=R
  because the regime rules would otherwise fire first on a perennial
  channel): R2/R3 -> NO-GO along the channel (a single bridge point
  is a separate MAYBE decision, not a routing MAYBE); R4/R5 ->
  MAYBE, bridge/boardwalk at a narrow point.
- W3: water regime H (permanently flooded), or Lacustrine UB open
  water, or PUB/PAB with H -> NO-GO. (Categorical H -> NO-GO is
  JUDGMENT J2.)
- W4: PFO2/PFO4/PSS2/3/4 with regime B/C (black spruce / tamarack
  bog, muskeg) -> NO-GO for a through-route; MAYBE only for a short,
  named, maintainable spur. The table row carries no size threshold,
  so no numeric "large" threshold is invented here; the spur
  exception is JUDGMENT J3.
- W5: regime F (semipermanently flooded) -> MAYBE, short narrow
  boardwalk only; NO-GO if the crossing exceeds ~300 ft (JUDGMENT
  J4) — a route-level check, noted in the popup, not applied here
  because this layer has no proposed tread.
- W6: regime C/E -> MAYBE, bog bridge/boardwalk, short crossing
  only. Regime D (continuously saturated) is treated as W6-analog
  MAYBE — the report's rules do not name D; this placement is
  chapter JUDGMENT, recorded in the feature's rule field.
- W7: regime A/B -> MAYBE, turnpike/puncheon.
- W9: modifier d (partly drained/ditched), f (farmed) or x
  (excavated), or class US (shore) -> MAYBE, field-check first; do
  NOT downgrade to GO. (MAYBE placement JUDGMENT J6.)
- Regime G (intermittently exposed) -> MAYBE, W9-analog (shore-like);
  chapter JUDGMENT, recorded in the rule field.
- Any code that matches none of the above (blank/unknown regime) ->
  MAYBE, "unclassified — field-check", chapter JUDGMENT.
- W2 (overlay: DNR public waters, calcareous fen, MBS rare natural
  community -> NO-GO pending agency advice) is NOT applied: NWI
  alone cannot identify these and the viewer has no public-waters /
  Natural Heritage layer yet. Recorded as an open gap in the
  metadata and SOURCES.md, not hidden. The popup carries the
  "check DNR public-waters/fen layers before routing" note.
- W10 (cumulative MAYBE length >~1/2 mile -> NO-GO, JUDGMENT J7)
  is a route-level rule, not a polygon rule; noted in SOURCES.md.
- Every feature carries `rating` (maybe | nogo), `rule` (the rule
  that fired, e.g. W6), and `structure` (the recommended structure
  or action). The GO/MAYBE/NO-GO mapping itself is chapter policy
  (the report: no published Cowardin -> GO/MAYBE/NO-GO matrix
  exists); every judgment is labelled in the rule field / SOURCES.md.

DISSOLVE: after clipping to the corridor, touching polygons with the
same (rating, Cowardin code) are merged into connected components
(unary_union per group, exploded to one feature per component), so
the file stays small and each feature is one wet complex, not one
photointerpreted sliver. `n_polygons` records how many source
polygons merged into the feature; `acres` is computed from the
clipped geometry.

Output: site/data/wetlands-nwi-minnesota.geojson (ONE file) + raw
fetch in working/nwi/raw-nwi.geojson + this pull log.

Usage: python3 scripts/pull_nwi_corridor.py
"""

import json
import math
import os
import re
import time
import urllib.parse

import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "working", "nwi")
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}
PULLED = time.strftime("%Y-%m-%d", time.gmtime())

NWI = ("https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/"
       "USA_Wetlands/FeatureServer/0")

BUFFER_KM = 3.21869  # 2 miles, same as the timber layer
KX = 111.320 * 0.6820  # km per degree lon at 47 N
KY = 111.195           # km per degree lat

WEST = {"Wilkin", "Otter Tail", "Becker", "Hubbard", "Clearwater"}
CENTRAL = {"Cass", "Itasca"}
ARROWHEAD = {"St. Louis", "Carlton", "Lake", "Cook"}

# Cowardin code: System [Subsystem digit] Class(2) [Subclass digit]
# [Regime letter] [modifier letters]. Split classes (PFO1/EM1C) take
# the first class/subclass.

REGIME_NAMES = {
    "A": "Temporarily flooded", "B": "Saturated",
    "C": "Seasonally flooded", "D": "Continuously saturated",
    "E": "Seasonally flooded/saturated",
    "F": "Semipermanently flooded", "G": "Intermittently exposed",
    "H": "Permanently flooded",
    "J": "Intermittently flooded", "K": "Artificially flooded",
}
SYSTEM_NAMES = {"P": "Palustrine", "L": "Lacustrine", "R": "Riverine",
                "E": "Estuarine", "M": "Marine"}


def fetch_json(url, retries=4):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("GET %s failed after %d tries: %s"
                       % (url[:200], retries, last_err))


def to_km_geom(geom):
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


CLASSES = {"AB", "EM", "FO", "SS", "UB", "US", "SB", "RB"}


def parse_code(code):
    """Parse a Cowardin code into (system, subsystem, [(class, subclass),
    ...], regime, modifiers).

    Parsed left-to-right against the known class set, so a code with
    no regime (e.g. PUS = Palustrine Unconsolidated Shore) is not
    misread as regime 'S', and split classes (e.g. PFO1/4D, where
    the second part is a bare subclass digit + regime) keep their
    regime — the regime/modifiers sit at the END of the full code.
    First-attempt bug, 2026-11-18: taking the first '/'-part alone
    lost the regime on 45 split-class polygons in an Itasca test
    box. All class/subclass pairs are returned; the bog rule (W4)
    fires if ANY pair is a bog class.
    Falls back to ('', '', [], '', '') on failure."""
    if not code:
        return ("", "", [], "", "")
    code = code.strip()
    system = code[0]
    if system not in "PLREM":
        return ("", "", [], "", "")
    rest = code[1:]
    sub = ""
    if rest and rest[0].isdigit():
        sub = rest[0]
        rest = rest[1:]
    parts = rest.split("/")
    pairs = []
    regime = ""
    mods = ""
    for i, part in enumerate(parts):
        last = (i == len(parts) - 1)
        if not part:
            return ("", "", [], "", "")
        if part[0].isalpha():
            m = re.match(r"^([A-Z]{2})(\d)?(.*)$", part)
            if not m or m.group(1) not in CLASSES:
                return ("", "", [], "", "")
            cls, subclass, tail = m.groups()
            pairs.append((cls, subclass or ""))
        elif part[0].isdigit() and pairs:
            m = re.match(r"^(\d)(.*)$", part)
            pairs.append((pairs[-1][0], m.group(1)))
            tail = m.group(2)
        else:
            return ("", "", [], "", "")
        if last:
            tm = re.match(r"^([A-Z])?([a-z]*)$", tail)
            if not tm:
                return ("", "", [], "", "")
            regime = tm.group(1) or ""
            mods = tm.group(2) or ""
        elif tail:
            return ("", "", [], "", "")
    return (system, sub, pairs, regime, mods)


def classify(attrs):
    """Return (rating, rule, structure, note) for one NWI polygon.

    rating: 'maybe' | 'nogo'. (GO is absence — no feature.)
    rule: the rule id that fired, with judgment tags where the report
    marks the placement as judgment.
    """
    code = (attrs.get("ATTRIBUTE") or "").strip()
    system, sub, pairs, regime, mods = parse_code(code)
    # Fall back to the service's parsed fields when the code won't parse.
    if not system:
        system = (attrs.get("SYSTEM") or "")[:1]
        pairs = [((attrs.get("CLASS") or "")[:2],
                  str(attrs.get("SUBCLASS") or "")[:1])]
        regime = (attrs.get("WATER_REGIME") or "")[:1]
        mods = (attrs.get("MODIFIER1") or "")[:1].lower()
    wet_type = attrs.get("WETLAND_TYPE") or ""
    classes = {c for c, _ in pairs}

    # W8 — riverine first (see module docstring: table-row precedence).
    if system == "R":
        if sub in ("2", "3"):
            return ("nogo", "W8",
                    "No tread along the channel; a single bridge point "
                    "is a separate project decision, not a routing MAYBE",
                    "Perennial riverine (R2/R3). Stay 25 ft from the "
                    "stream edge except at the crossing.")
        return ("maybe", "W8",
                "Bridge / boardwalk at a narrow point only",
                "Intermittent riverine (R4/R5).")
    # W3 — open / permanent water.
    if regime == "H" or (system == "L" and "UB" in classes) or \
            (classes & {"PUB", "PAB"} and regime == "H"):
        return ("nogo", "W3",
                "Avoid — reroute around; a bridge is a bridge project, "
                "not a trail-routing MAYBE",
                "Permanently flooded / open water (%s)." % code)
    # W4 — large bog / muskeg complex. Fires if ANY part of a split
    # class is a bog class (e.g. PFO1/4C contains PFO4).
    bog = any((c == "FO" and s in ("2", "4")) or
              (c == "SS" and s in ("2", "3", "4")) for c, s in pairs)
    if bog and regime in ("B", "C"):
        return ("nogo", "W4",
                "Avoid for a through-route; MAYBE only for a short, "
                "named, maintainable spur on bog bridge",
                "Black spruce / tamarack bog or bog shrub (%s, regime "
                "%s). NPS Arrowhead precedent: 70 mi of this swamp was "
                "left unbuilt and rerouted." % (code, regime))
    # W5 — semipermanently flooded.
    if regime == "F":
        return ("maybe", "W5",
                "Short, narrow boardwalk only; NO-GO if the crossing "
                "exceeds ~300 ft",
                "Semipermanently flooded — surface water persists most "
                "of the growing season.")
    # W6 — seasonally flooded/saturated (+ D as W6-analog, judgment).
    if regime in ("C", "E"):
        return ("maybe", "W6",
                "Bog bridge / boardwalk, short crossing only — narrow "
                "point, perpendicular, spanning the full saturated width",
                "Seasonally flooded/saturated (%s)."
                % REGIME_NAMES.get(regime, regime))
    if regime == "D":
        return ("maybe", "W6-analog",
                "Bog bridge / boardwalk, short crossing only",
                "Continuously saturated.")
    # W7 — temporarily flooded / saturated.
    if regime in ("A", "B"):
        return ("maybe", "W7",
                "Turnpike / puncheon — edge crossing, shortest "
                "distance, perpendicular",
                "Temporarily flooded/saturated (%s); field-check peat "
                "depth." % REGIME_NAMES.get(regime, regime))
    # W9 — modifiers / shore; G regime (W9-analog, judgment).
    if mods and any(c in mods for c in "dfx"):
        return ("maybe", "W9",
                "Field-check first — do NOT assume degraded = GO; "
                "LGU/TEP determination required",
                "Modifier '%s' (ditched/farmed/excavated) — WCA/404 "
                "status is not removed by the modifier." % mods)
    if "US" in classes or regime in ("G", "K"):
        if regime == "K":
            return ("maybe", "W9-analog",
                    "Field-check first",
                    "Artificially flooded — water level is managed "
                    "(%s)." % code)
        return ("maybe", "W9-analog",
                "Field-check first",
                "Shore / intermittently exposed (%s)." % code)
    # Anything else: unclassified regime — MAYBE, field-check.
    return ("maybe", "UNCLASSIFIED",
            "Field-check first",
            "Cowardin code %s (%s) matched no classification rule."
            % (code, wet_type))


# Canonical rule text — the single source of truth for the viewer popup
# (site/app.js WETLAND_RULES mirrors this table) and for SOURCES.md.
# The GeoJSON carries only the short rule id; the popup composes the
# structure + note from this table and the feature's own attributes
# (code, regime, regime_name, modifier, wetland_type).
# Placeholders: {code} Cowardin code, {regime} regime letter,
# {regime_name} regime in words, {mods} modifier letters,
# {wet_type} wetland type. "judgment" is the J-register tag, or null.
RULE_TEXT = {
    "W3": {"structure": "Avoid — reroute around; a bridge is a bridge "
                        "project, not a trail-routing MAYBE",
           "note": "Permanently flooded / open water ({code}).",
           "judgment": "J2: categorical H→NO-GO is judgment"},
    "W4": {"structure": "Avoid for a through-route; MAYBE only for a "
                        "short, named, maintainable spur on bog bridge",
           "note": "Black spruce / tamarack bog or bog shrub ({code}, "
                   "regime {regime}). NPS Arrowhead precedent: 70 mi of "
                   "this swamp was left unbuilt and rerouted.",
           "judgment": "J3: spur exception, no numeric size threshold — "
                       "table row applied as written"},
    "W5": {"structure": "Short, narrow boardwalk only; NO-GO if the "
                        "crossing exceeds ~300 ft",
           "note": "Semipermanently flooded — surface water persists "
                   "most of the growing season.",
           "judgment": "J4: >~300 ft of F-regime tread = NO-GO, "
                       "route-level check"},
    "W6": {"structure": "Bog bridge / boardwalk, short crossing only — "
                        "narrow point, perpendicular, spanning the full "
                        "saturated width",
           "note": "Seasonally flooded/saturated ({regime_name}).",
           "judgment": None},
    "W6-analog": {"structure": "Bog bridge / boardwalk, short crossing "
                               "only",
                  "note": "Continuously saturated.",
                  "judgment": "Report rules do not name regime D; treated "
                             "as seasonally saturated"},
    "W7": {"structure": "Turnpike / puncheon — edge crossing, shortest "
                        "distance, perpendicular",
           "note": "Temporarily flooded/saturated ({regime_name}); "
                   "field-check peat depth.",
           "judgment": "J5: rod-sounding field upgrade — if a rod meets "
                       "no resistance, upgrade to NO-GO"},
    "W8": {"nogo": {"structure": "No tread along the channel; a single "
                                 "bridge point is a separate project "
                                 "decision, not a routing MAYBE",
                    "note": "Perennial riverine (R2/R3). Stay 25 ft from "
                            "the stream edge except at the crossing.",
                    "judgment": None},
           "maybe": {"structure": "Bridge / boardwalk at a narrow point "
                                  "only",
                     "note": "Intermittent riverine (R4/R5).",
                     "judgment": None}},
    "W9": {"structure": "Field-check first — do NOT assume degraded = "
                        "GO; LGU/TEP determination required",
           "note": "Modifier '{mods}' (ditched/farmed/excavated) — "
                   "WCA/404 status is not removed by the modifier.",
           "judgment": "J6: MAYBE placement is judgment"},
    "W9-analog": {"structure": "Field-check first",
                  "note": "Shore / intermittently exposed ({code}).",
                  "note_k": "Artificially flooded — water level is "
                            "managed ({code}).",
                  "judgment": "Shore / intermittently exposed treated as "
                             "W9 MAYBE; regime K (artificially flooded) "
                             "treated the same way"},
    "UNCLASSIFIED": {"structure": "Field-check first",
                     "note": "Cowardin code {code} ({wet_type}) matched "
                             "no classification rule.",
                     "judgment": "No rule in W1-W10 names this code; "
                                "field-check, do not assume GO"},
}


def post_query(params, retries=4):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(NWI + "/query", data=params, headers=UA,
                              timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("POST query failed after %d tries: %s"
                       % (retries, last_err))


def arcgis_rings(geom):
    """Shapely (Multi)Polygon -> ArcGIS JSON rings.

    ArcGIS convention is exterior rings clockwise, holes
    counter-clockwise (opposite of GeoJSON's right-hand rule), so
    orient each part with sign=-1.0 before emitting rings."""
    from shapely.geometry import Polygon as _P
    from shapely.geometry import MultiPolygon as _MP
    from shapely.geometry.polygon import orient as _orient
    rings = []
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" \
        else [geom]
    for pg in polys:
        pg = _orient(pg, sign=-1.0)
        rings.append([[round(x, 5), round(y, 5)]
                      for x, y in pg.exterior.coords])
        for hole in pg.interiors:
            rings.append([[round(x, 5), round(y, 5)]
                          for x, y in hole.coords])
    return rings


def fetch_cell(cell_geom):
    """Fetch all NWI features intersecting one cell's corridor slice.

    Returns (features, count) — count is the service's returnCountOnly
    for the same geometry, cross-checked against len(features)."""
    rings = arcgis_rings(cell_geom)
    geom = {"rings": rings, "spatialReference": {"wkid": 4326}}
    base = {"geometry": json.dumps(geom),
            "geometryType": "esriGeometryPolygon", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects"}
    count = post_query(dict(base, where="1=1", returnCountOnly="true",
                            f="json")).get("count")
    fields = ("OBJECTID,ATTRIBUTE,WETLAND_TYPE,SYSTEM,SUBSYSTEM,CLASS,"
              "SUBCLASS,WATER_REGIME,MODIFIER1,MODIFIER2,Shape__Area")
    out = []
    offset = 0
    while True:
        params = dict(base, where="1=1", outFields=fields, outSR="4326",
                      maxAllowableOffset="0.0002", geometryPrecision="5",
                      orderByFields="OBJECTID", resultOffset=str(offset),
                      resultRecordCount="1000", returnGeometry="true",
                      f="geojson")
        gj = post_query(params)
        page = gj.get("features", [])
        out.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    return out, count


def fetch_all(corridor, env):
    """Per-cell corridor-slice geometry queries (POST). Returns the
    deduped list of raw service features."""
    from shapely.geometry import box as _box
    cells = []
    x = math.floor(env[0] * 4) / 4.0
    while x < env[2]:
        y = math.floor(env[1] * 4) / 4.0
        while y < env[3]:
            cell = _box(x, y, min(x + 0.25, env[2]),
                        min(y + 0.25, env[3]))
            if cell.intersects(corridor):
                cells.append(cell)
            y += 0.25
        x += 0.25
    print("%d corridor cells (0.25 deg)" % len(cells), flush=True)

    seen_ids = set()
    feats = []
    for ci, cell in enumerate(cells):
        # Query geometry: the cell's slice of the corridor, simplified
        # then widened 0.5 km so the query is a superset of the exact
        # corridor (the exact clip happens in Python below).
        slice_geom = cell.intersection(corridor)
        qgeom = to_lonlat_geom(to_km_geom(
            slice_geom.simplify(0.002)).buffer(0.5))
        cell_feats, count = fetch_cell(qgeom)
        if count is not None and len(cell_feats) != count:
            print("  WARNING cell %d: fetched %d vs count %d"
                  % (ci + 1, len(cell_feats), count), flush=True)
        new = 0
        for f in cell_feats:
            oid = (f.get("properties") or {}).get("OBJECTID")
            if oid is None or oid not in seen_ids:
                seen_ids.add(oid)
                feats.append(f)
                new += 1
        print("  cell %d/%d: %d fetched (%d new, running unique %d)"
              % (ci + 1, len(cells), len(cell_feats), new, len(feats)),
              flush=True)
    print("unique corridor features fetched: %d" % len(feats), flush=True)
    return feats


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-raw", action="store_true",
                    help="skip the service fetch; reprocess "
                         "working/nwi/raw-nwi.geojson (clip/classify/"
                         "dissolve/write only)")
    args = ap.parse_args()

    corridor = build_corridor()
    env = corridor.bounds
    print("corridor envelope: lon %.4f..%.4f lat %.4f..%.4f"
          % (env[0], env[2], env[1], env[3]), flush=True)

    if args.from_raw:
        with open(os.path.join(WORK, "raw-nwi.geojson")) as fh:
            feats = json.load(fh)["features"]
        print("from raw: %d features" % len(feats), flush=True)
    else:
        feats = fetch_all(corridor, env)
        with open(os.path.join(WORK, "raw-nwi.geojson"), "w") as fh:
            json.dump({"type": "FeatureCollection", "features": feats}, fh)
        print("wrote working/nwi/raw-nwi.geojson", flush=True)



    # ---- county lookup (same TIGERweb polygons as the timber pull)
    counties = json.load(open(os.path.join(
        REPO, "working", "timber-statewide", "mn-counties.geojson")))
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

    # ---- normalize + clip + classify
    from collections import Counter
    grouped = {}  # (rating, code) -> list of (geom, props)
    skipped = {"no_geometry": 0, "outside_corridor": 0, "invalid": 0,
               "unparsed_code": 0}
    rating_counts = Counter()
    code_counts = Counter()
    for f in feats:
        props = f.get("properties") or {}
        try:
            g = shape(f["geometry"])
        except Exception:
            skipped["no_geometry"] += 1
            continue
        if g.is_empty or not g.is_valid:
            try:
                g = g.buffer(0)
            except Exception:
                skipped["invalid"] += 1
                continue
            if g.is_empty:
                skipped["invalid"] += 1
                continue
        c = g.intersection(corridor)
        if c.is_empty:
            skipped["outside_corridor"] += 1
            continue
        code = (props.get("ATTRIBUTE") or "").strip()
        if not parse_code(code)[0]:
            skipped["unparsed_code"] += 1
        rating, rule, structure, note = classify(props)
        rating_counts[rating] += 1
        code_counts[code] += 1
        key = (rating, code)
        grouped.setdefault(key, []).append((c, props, rating, rule,
                                            structure, note))
    print("clipped polygons: %d (skipped %s)"
          % (sum(rating_counts.values()), skipped), flush=True)
    print("by rating (pre-dissolve):", dict(rating_counts), flush=True)

    # ---- dissolve connected components per (rating, code)
    out_feats = []
    for (rating, code), items in sorted(grouped.items()):
        geoms = [it[0] for it in items]
        merged = unary_union(geoms)
        parts = list(merged.geoms) if merged.geom_type == "MultiPolygon" \
            else [merged]
        rep = items[0]
        _, _, _, rule, structure, note = rep
        props0 = rep[1]
        system, _, pairs, regime, mods = parse_code(code)
        cls = "/".join(c for c, _ in pairs)
        subclass = "/".join(s for _, s in pairs if s)
        for pg in parts:
            if pg.is_empty:
                continue
            gkm = to_km_geom(pg)
            acres = round(gkm.area * 247.105, 1)
            county = county_of(pg)
            coords = [[[round(x, 4), round(y, 4)] for x, y in ring.coords]
                      for ring in [pg.exterior] + list(pg.interiors)]
            out_feats.append({
                "type": "Feature",
                "properties": {
                    "code": code,
                    "wetland_type": props0.get("WETLAND_TYPE"),
                    "system": SYSTEM_NAMES.get(system, system),
                    "class": cls,
                    "subclass": subclass,
                    "regime": regime,
                    "regime_name": REGIME_NAMES.get(regime),
                    "modifier": mods or None,
                    "rating": rating,
                    "rule": rule,
                    "acres": acres,
                    "n_polygons": len(items),
                    "county": county,
                    "region": region_of(county),
                },
                "geometry": {"type": "Polygon", "coordinates": coords},
            })
    print("dissolved features: %d" % len(out_feats), flush=True)

    from collections import Counter as _C
    by_rating = _C(f["properties"]["rating"] for f in out_feats)
    by_county = _C(f["properties"]["county"] for f in out_feats)
    by_region = _C(f["properties"]["region"] for f in out_feats)
    total_acres = sum(f["properties"]["acres"] for f in out_feats)
    xs, ys = [], []
    for feat in out_feats:
        b = shape(feat["geometry"]).bounds
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]

    doc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("USFWS National Wetlands Inventory along the full "
                        "Minnesota North Country Trail — 2-mile corridor, "
                        "classified GO / MAYBE / NO-GO for trail routing"),
            "corridor": ("Statewide NCT line (site/data/trail-minnesota."
                         "geojson, 348 features) buffered 2 mi (3,218.69 "
                         "m); a wetland counts when its polygon intersects "
                         "the buffer"),
            "service": NWI,
            "service_note": ("Task brief named the fws.gov MapServer URL; "
                             "it returns 404 — the service moved to ArcGIS "
                             "Online (this URL). The DNR's own updated-NWI "
                             "service is token-gated (499) and not publicly "
                             "queryable. Minnesota content in the national "
                             "file is the DNR June 2019 update delivered to "
                             "FWS. Per-polygon vintage is NOT exposed by "
                             "this service — recorded as a limit."),
            "classification": ("Rules W1-W10 / C1-C4 from the Nov 18 2026 "
                               "classification sweep (research_notes/nwi-"
                               "wetland-trail-classification-20261118-1744/"
                               "report.md). GO is absence of a polygon "
                               "(W1) — no GO features exist in this file. "
                               "The GO/MAYBE/NO-GO mapping is chapter "
                               "policy: no published Cowardin matrix "
                               "exists; every judgment is labelled in the "
                               "feature's rule field."),
            "open_gaps": ("W2 overlay (DNR public waters, calcareous "
                          "fen, MBS rare natural community) NOT applied — "
                          "NWI alone cannot identify these and the viewer "
                          "has no public-waters / Natural Heritage layer "
                          "yet. W10 cumulative MAYBE length (>~1/2 mi) is "
                          "a route-level rule, not a polygon rule."),
            "simplification": ("Server-side maxAllowableOffset 0.0002 "
                               "(~22 m) + geometryPrecision 5; measured "
                               "2026-11-18: 200-feature Itasca sample "
                               "1,614,232 bytes raw -> 51,953 bytes, 0 "
                               "empty geometries, smallest polygon 856 m2 "
                               "intact. Dissolved into connected "
                               "components per (rating, Cowardin code)."),
            "pulled_utc_date": PULLED,
            "features_total": len(out_feats),
            "features_by_rating": dict(by_rating),
            "features_by_region": dict(by_region),
            "features_by_county": dict(by_county),
            "source_polygons": sum(rating_counts.values()),
            "source_polygons_by_rating": dict(rating_counts),
            "top_codes": dict(code_counts.most_common(15)),
            "total_acres": round(total_acres, 1),
            "skipped": skipped,
            "extent_lon": [round(min(xs), 4), round(max(xs), 4)],
            "extent_lat": [round(min(ys), 4), round(max(ys), 4)],
            "note": ("Do NOT use the county wetlands.zip (46.4 MB, 2017 "
                     "vintage) — flagged STALE in the Nov 11 useful-layers "
                     "doc. NWI is a screening layer, not a delineation: "
                     "identification ~90%, classification ~75%, 95% of "
                     "features within +/-5.9 m; TMU 0.5 ac. Field "
                     "delineation + permits before any MAYBE becomes a "
                     "route."),
        },
        "features": out_feats,
    }
    out_path = os.path.join(REPO, "site", "data",
                            "wetlands-nwi-minnesota.geojson")
    with open(out_path, "w") as fh:
        json.dump(doc, fh)
    print("WROTE %s: %d features, %.1f ac (%d bytes)"
          % (out_path, len(out_feats), total_acres,
             os.path.getsize(out_path)), flush=True)
    print("by rating:", dict(by_rating), flush=True)
    print("by region:", dict(by_region), flush=True)
    print("by county:", dict(by_county), flush=True)
    print("skipped:", skipped, flush=True)
    print("extent lon %.4f..%.4f lat %.4f..%.4f"
          % (min(xs), max(xs), min(ys), max(ys)), flush=True)
    with open(os.path.join(WORK, "wetland-rules.json"), "w") as fh:
        json.dump(RULE_TEXT, fh, indent=1)
    print("wrote working/nwi/wetland-rules.json", flush=True)


if __name__ == "__main__":
    main()

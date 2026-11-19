#!/usr/bin/env python3
"""Pull SSURGO soils for the Minnesota NCT corridor and classify them
for trail routing (report rules S1-S8 + combined C1-C4).

Sources
-------
- Classification: ~/workspace/research_notes/nwi-wetland-trail-classification-20261118-1744/report.md
  (M.4 S1-S8, M.5 C1-C4, M.6 judgment register J8-J12).
- Data: USDA NRCS Soil Data Access (SDA) tabular REST, same service and
  query pattern as site/buildout/build-soils.py (Part A), which proved
  the pattern on 2026-11-13. Corridor: the same 2-mile buffer around
  the statewide trail line as the timber layer and the NWI pull
  (scripts/pull_nwi_corridor.py); reuses its saved corridor file when
  present so all three layers share one identical corridor.

Attributes pulled per map unit
------------------------------
- mapunit: musym, muname.
- muaggatt: urbrecptdcd (Paths and Trails rating, DOMINANT condition —
  the S1 backbone), urbrecptwta (weighted-average index), drclassdcd
  (drainage class), slopegradwta (representative slope %), flodfreqdcd
  (flooding frequency), pondfreqdcd (ponding frequency), wtdepannmin
  (minimum depth to water table, cm, annual).
- component (major components only): hydricrating, taxorder (soil
  order — Histosols = organic), comppct_r. % hydric of the map unit
  is summed over ALL components with hydricrating = 'Yes'.
- cointerp (probe): limiting reasons for the 'Paths and Trails'
  interpretation. The cointerp table is a rule tree: ruledepth = 0 is
  the aggregated rating; ruledepth = 1 rows are the individual
  limiting features (mrulename = feature name, e.g. 'Depth to
  saturated zone'; interphr = that feature's rating value, 0-1).
  If the probe returns nothing the file is still written with the
  rating + attributes and reasons=None — the gap is logged, not fatal.

Classification (S1-S8), applied per map unit
--------------------------------------------
- S1: backbone = urbrecptdcd (dominant condition). Wettest component
  and % hydric recorded separately (S6/S8).
- S2 (JUDGMENT J8 — NRCS publishes a limitation rating, not a
  go/no-go): Not limited -> GO; Somewhat limited -> MAYBE;
  Very limited -> NO-GO.
- S3(a): drainage Poorly/Very poorly drained, OR ponding Frequent,
  OR flooding Frequent, OR wtdepannmin < 30 cm (~1 ft) -> NO-GO for
  ground tread (elevated crossing only). The <1 ft cut-off is
  JUDGMENT J9 — no source states it as a threshold.
- S3(b): major component is a Histosol (organic soil: peat/muck) ->
  NO-GO for ground tread.
- S3(c)/(d) texture splits (clay vs sand): texture never overrides
  wetness or grade (report §11 summary), so no override is applied;
  drainage + slope are carried on the feature so a reader can apply
  S3(c)/(d) by eye.
- S4 grade/alignment (TG/TSA from 1-m LiDAR): NOT computable at the
  map-unit level — it depends on the actual trail alignment, which
  does not exist yet. Recorded as a route-level check in the popup
  note, not applied in the layer.
- S5: IMBA grade maxima NOT used (no empirical data cited).
- S6: hydric MAJOR component -> suspected wetland (C3): a GO rating
  is downgraded to MAYBE; the soil rating alone never makes it GO.
  Hydric MINOR component only -> note % hydric, field-check the low
  spot. The 10% minor-component figure is JUDGMENT J11.
- S7: frost action, K-factor, T-factor, hydrologic group, Ksat,
  AASHTO/USCS, shrink-swell, depth to bedrock, AWC, pH, EC are NOT
  used as routing attributes (recorded exclusion).
- S8: read at component level — the file carries the dominant rating
  AND the wettest-component / % hydric fields, never the map-unit
  name alone.

Combined rules (C1-C4): the soils file carries the SOILS rating only.
C1 (stricter governs) and C2 (soil cannot rescue a wetland) are
applied where the two layers are read together — in the viewer the
wetlands overlay sits above soils and the popup carries the C4
caveat. C4: GO requires BOTH no NWI polygon AND a Not-limited soil
(plus a side-hill 3-10% alignment, S4) — screening only, because
both datasets miss small features (SSURGO minimum delineation
1.4-5.7 ac depending on scale).

Output
------
- site/data/soils-ssurgo-minnesota.geojson — dissolved by mukey
  (connected components), simplified ~70-90 m, coordinates rounded
  to 4 decimals. Every feature carries rating (go|maybe|nogo),
  rule (firing rules + judgment tags), nrcs_rating, reasons,
  drainage, hydric_pct, hydric_major, slope, flood, pond,
  wtdepannmin_cm, musym, muname, acres, county, region, source.
- working/ssurgo/raw-attrs-<date>.json — per-mukey attributes.
- working/ssurgo/pull-run-<date>.log — run log (stdout is tee'd here).

SDA outage note (2026-11-18): SDA returned HTTP 502 on both hosts
(sdmdataaccess.sc.egov.usda.gov and sdmdataaccess.nrcs.usda.gov,
tabular + spatial) all evening. This script fails fast with a clear
message when SDA is down; re-run when it recovers. No working
fallback was found: the Esri Living Atlas 'USA Soils Map Units'
FeatureServer returns 499 Token Required.
"""
import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import date

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import to_wkt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'site', 'data')
WORK = os.path.join(BASE, 'working', 'ssurgo')
TRAIL = os.path.join(DATA, 'trail-minnesota.geojson')
NWI_CORRIDOR = os.path.join(BASE, 'working', 'nwi', 'corridor-2mi.geojson')
OUT = os.path.join(DATA, 'soils-ssurgo-minnesota.geojson')
SDA = 'https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
SDA_ALT = 'https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest'
UA = {'User-Agent': 'Mozilla/5.0 (ITM viewer soils pull)'}
TODAY = date.today().isoformat()

# Same corridor math as the timber pull and the NWI pull.
BUFFER_KM = 3.21869  # 2 miles
KX = 111.320 * math.cos(math.radians(47.0))
KY = 111.195


def to_km_geom(g):
    from shapely.affinity import scale
    return scale(g, xfact=KX, yfact=KY, origin=(0, 0))


def load_corridor():
    """Reuse the NWI pull's corridor file (identical corridor for all
    three layers); fall back to rebuilding it from the trail line."""
    if os.path.exists(NWI_CORRIDOR):
        with open(NWI_CORRIDOR) as f:
            gj = json.load(f)
        print('corridor: reused %s' % NWI_CORRIDOR)
        return shape(gj['geometry'])
    from shapely.geometry import MultiLineString
    with open(TRAIL) as f:
        gj = json.load(f)
    lines = [shape(feat['geometry']) for feat in gj['features']]
    merged = unary_union(lines)
    merged_km = to_km_geom(merged)
    buf = merged_km.buffer(BUFFER_KM)
    inv = buf
    from shapely.affinity import scale as _s
    corridor = _s(inv, xfact=1.0 / KX, yfact=1.0 / KY, origin=(0, 0))
    print('corridor: rebuilt from %s' % TRAIL)
    return corridor


def county_of(geom):
    """County + region of a geometry, from the timber pull's county file."""
    path = os.path.join(BASE, 'working', 'timber-statewide',
                        'mn-counties.geojson')
    if not hasattr(county_of, '_counties'):
        with open(path) as f:
            gj = json.load(f)
        county_of._counties = [(feat['properties']['NAME'],
                                shape(feat['geometry']))
                               for feat in gj['features']]
        county_of._regions = {
            'Wilkin': 'west', 'Otter Tail': 'west', 'Becker': 'west',
            'Hubbard': 'west', 'Cass': 'central', 'Crow Wing': 'central',
            'Aitkin': 'central', 'Carlton': 'central',
            'Itasca': 'arrowhead', 'St. Louis': 'arrowhead',
            'Lake': 'arrowhead', 'Cook': 'arrowhead'}
    c = geom.centroid
    for name, poly in county_of._counties:
        if poly.contains(c):
            return name, county_of._regions.get(name, 'central')
    return None, 'central'


def sda(sql, host=None, retries=3):
    """One SDA tabular query; returns the 'Table' rows (list of lists).
    Raises on HTTP failure after retries."""
    host = host or SDA
    data = json.dumps({'query': sql, 'format': 'JSON'}).encode()
    req = urllib.request.Request(host, data=data,
                                 headers={'Content-Type': 'application/json',
                                          **UA})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode('utf-8'))['Table']
        except urllib.error.HTTPError as e:
            last = e
            print('  SDA HTTP %s (attempt %d/%d): %s'
                  % (e.code, attempt + 1, retries, sql[:80]))
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            last = e
            print('  SDA error (attempt %d/%d): %r' % (attempt + 1, retries, e))
            time.sleep(5 * (attempt + 1))
    raise RuntimeError('SDA query failed after %d attempts: %s'
                       % (retries, last))


def sda_check():
    """Fail fast with a clear message if SDA is down (2026-11-18: 502)."""
    try:
        rows = sda('SELECT TOP 1 mukey FROM muaggatt', retries=1)
        print('SDA up: %s' % SDA)
        return True
    except Exception as e:
        print('SDA DOWN on %s: %r' % (SDA, e))
    try:
        rows = sda('SELECT TOP 1 mukey FROM muaggatt', host=SDA_ALT,
                   retries=1)
        print('SDA up (alt host): %s' % SDA_ALT)
        return True
    except Exception as e:
        print('SDA DOWN on alt host %s: %r' % (SDA_ALT, e))
    return False


# ---------------------------------------------------------------- classify

RATING_MAP = {'Not limited': 'go', 'Somewhat limited': 'maybe',
              'Very limited': 'nogo'}


def classify(a):
    """Return (rating, rule, note) for one map unit's attributes.

    a: dict with nrcs_rating, drainage, slope, flood, pond,
    wtdepannmin_cm, hydric_major, hydric_pct, histosol, reasons.
    rating: 'go' | 'maybe' | 'nogo'."""
    nrcs = a.get('nrcs_rating')
    rules = []
    if not nrcs or nrcs not in RATING_MAP:
        return ('maybe',
                'UNCLASSIFIED (judgment: no Paths and Trails rating '
                'returned for this map unit; field-check, do not assume GO)',
                'No NRCS Paths and Trails rating — field-check before '
                'routing tread here.')
    rating = RATING_MAP[nrcs]
    rules.append('S1/S2: %s -> %s (J8: GO/MAYBE/NO-GO mapping is the '
                 "chapter's, not NRCS's)" % (nrcs, rating.upper()))
    # S3(a) — wetness override.
    wet = []
    dr = (a.get('drainage') or '')
    if dr in ('Poorly drained', 'Very poorly drained'):
        wet.append('drainage %s' % dr.lower())
    if (a.get('pond') or '') == 'Frequent':
        wet.append('frequent ponding')
    if (a.get('flood') or '') == 'Frequent':
        wet.append('frequent flooding')
    wt = a.get('wtdepannmin_cm')
    if wt is not None and wt < 30:
        wet.append('depth to saturated zone %d cm (<~1 ft)' % wt)
    if wet:
        rating = 'nogo'
        rules.append('S3(a): %s -> NO-GO for ground tread (elevated '
                     'crossing only); <1 ft cut-off is JUDGMENT J9'
                     % '; '.join(wet))
    # S3(b) — organic soil.
    if a.get('histosol'):
        rating = 'nogo'
        rules.append('S3(b): Histosol (organic soil: peat/muck) -> '
                     'NO-GO for ground tread')
    # S6 — hydric major component: suspected wetland (C3).
    if a.get('hydric_major') == 'Yes' and rating == 'go':
        rating = 'maybe'
        rules.append('S6/C3: hydric MAJOR component -> suspected '
                     'wetland; soil rating alone never makes it GO')
    elif a.get('hydric_major') == 'Yes':
        rules.append('S6/C3: hydric MAJOR component — suspected wetland; '
                     'see NWI overlay (C1: stricter governs)')
    note_bits = []
    if a.get('reasons'):
        note_bits.append('Limiting reasons: %s'
                         % '; '.join('%s %.2f' % (k, v)
                                     for k, v in a['reasons']))
    if a.get('hydric_pct'):
        note_bits.append('%d%% hydric by component'
                         % a['hydric_pct'])
    if a.get('drainage'):
        note_bits.append('drainage: %s' % a['drainage'])
    if a.get('slope') is not None:
        note_bits.append('representative slope %.1f%%' % a['slope'])
    note_bits.append('S4 grade/alignment (TG/TSA from LiDAR) is a '
                     'route-level check — not applied at the map-unit '
                     'level; a Not-limited soil on a fall-line grade '
                     '>11% is not a sustainable GO.')
    if rating == 'go':
        note_bits.append('C4: GO only as screening — requires NO NWI '
                         'polygon here too, plus a side-hill 3-10% '
                         'alignment and a field walk confirming mineral '
                         'tread.')
    return (rating, ' + '.join(rules), ' '.join(note_bits))


# ---------------------------------------------------------------- main

def main():
    os.makedirs(WORK, exist_ok=True)
    t0 = time.time()
    corridor = load_corridor()
    polys = list(corridor.geoms) if corridor.geom_type == 'MultiPolygon' \
        else [corridor]
    print('corridor: %d polygon(s); envelope lon %.4f..%.4f lat %.4f..%.4f'
          % (len(polys), corridor.bounds[0], corridor.bounds[2],
             corridor.bounds[1], corridor.bounds[3]))

    if not sda_check():
        print('ABORT: NRCS Soil Data Access is down (both hosts). '
              'Re-run when it recovers. No working fallback exists '
              '(Esri USA_Soils_Map_Units is token-gated, 499).')
        sys.exit(3)

    # ---- mukeys + mupolygonkeys intersecting the corridor ----
    mukeys = set()
    polykeys = set()
    for i, poly in enumerate(polys):
        wkt = to_wkt(poly.simplify(0.002), rounding_precision=5)
        for (mk,) in sda(
                "SELECT mukey FROM "
                "SDA_Get_Mukey_from_intersection_with_WktWgs84('%s')" % wkt):
            mukeys.add(int(mk))
        for (pk,) in sda(
                "SELECT mupolygonkey FROM "
                "SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('%s')"
                % wkt):
            polykeys.add(int(pk))
        print('  corridor poly %d/%d: %d mukeys, %d mupolygonkeys'
              % (i + 1, len(polys), len(mukeys), len(polykeys)))
    mukey_list = sorted(mukeys)
    print('unique mukeys: %d; unique mupolygonkeys: %d'
          % (len(mukey_list), len(polykeys)))

    # ---- attributes, in chunks of 200 ----
    attrs = {}
    for i in range(0, len(mukey_list), 200):
        chunk = mukey_list[i:i + 200]
        inlist = ','.join(str(m) for m in chunk)
        for (mk, musym, muname) in sda(
                'SELECT mukey, musym, muname FROM mapunit '
                'WHERE mukey IN (%s)' % inlist):
            attrs.setdefault(int(mk), {}).update(
                {'musym': musym, 'muname': muname})
        for row in sda(
                'SELECT mukey, drclassdcd, slopegradwta, flodfreqdcd, '
                'pondfreqdcd, wtdepannmin, urbrecptdcd, urbrecptwta '
                'FROM muaggatt WHERE mukey IN (%s)' % inlist):
            mk = int(row[0])
            attrs.setdefault(mk, {}).update({
                'drainage': row[1], 'slope': row[2], 'flood': row[3],
                'pond': row[4], 'wtdepannmin_cm': row[5],
                'nrcs_rating': row[6], 'nrcs_index': row[7]})
        # component level: major components (hydric, order) + % hydric
        comp_hyd = defaultdict(float)
        for (mk, hr, pct) in sda(
                'SELECT mukey, hydricrating, comppct_r FROM component '
                'WHERE mukey IN (%s)' % inlist):
            if hr == 'Yes':
                comp_hyd[int(mk)] += float(pct or 0)
        for (mk, hr, taxorder) in sda(
                "SELECT mukey, hydricrating, taxorder FROM component "
                "WHERE mukey IN (%s) AND majcompflag = 'Yes'" % inlist):
            mk = int(mk)
            d = attrs.setdefault(mk, {})
            if hr == 'Yes':
                d['hydric_major'] = 'Yes'
            elif 'hydric_major' not in d:
                d['hydric_major'] = hr
            if (taxorder or '') == 'Histosols':
                d['histosol'] = True
        for mk, pct in comp_hyd.items():
            attrs.setdefault(mk, {})['hydric_pct'] = round(pct)
        print('  attrs chunk %d-%d' % (i, min(i + 200, len(mukey_list))))

    # ---- cointerp probe: limiting reasons for Paths and Trails ----
    reasons = {}  # mukey -> [(feature, interphr)] sorted desc
    try:
        probe = sda(
            "SELECT TOP 5 cokey, mrulename, interphr, interphrc, "
            "ruledepth FROM cointerp WHERE mrulename LIKE "
            "'%Paths and Trails%' AND ruledepth = 1", retries=1)
        print('cointerp probe: %d sample rows: %s' % (len(probe), probe))
        if probe:
            for i in range(0, len(mukey_list), 200):
                chunk = mukey_list[i:i + 200]
                inlist = ','.join(str(m) for m in chunk)
                rows = sda(
                    'SELECT mu.mukey, co.mrulename, co.interphr '
                    'FROM mapunit AS mu '
                    'INNER JOIN component AS c ON c.mukey = mu.mukey '
                    'INNER JOIN cointerp AS co ON co.cokey = c.cokey '
                    "AND co.ruledepth = 1 AND co.mrulename LIKE "
                    "'%Paths and Trails%' "
                    'WHERE mu.mukey IN (%s)' % inlist)
                per = defaultdict(dict)
                for (mk, feat, val) in rows:
                    mk = int(mk)
                    try:
                        v = float(val)
                    except (TypeError, ValueError):
                        continue
                    if v > per[mk].get(feat, -1):
                        per[mk][feat] = v
                for mk, feats in per.items():
                    reasons[mk] = sorted(feats.items(),
                                         key=lambda kv: -kv[1])[:4]
                print('  reasons chunk %d-%d: %d mukeys with reasons'
                      % (i, min(i + 200, len(mukey_list)), len(reasons)))
            for mk, rs in reasons.items():
                attrs.setdefault(mk, {})['reasons'] = rs
        else:
            print('WARNING: cointerp probe returned 0 rows — reasons '
                  'will be None (file still usable; rating + attributes '
                  'present). Re-probe when SDA is healthy.')
    except Exception as e:
        print('WARNING: cointerp probe failed (%r) — reasons will be '
              'None (file still usable).' % e)

    with open(os.path.join(WORK, 'raw-attrs-%s.json' % TODAY), 'w') as f:
        json.dump({str(k): v for k, v in attrs.items()}, f, indent=1)
    print('raw attrs saved: %d mukeys' % len(attrs))

    # ---- polygons, by mupolygonkey ----
    feats = []  # (mukey, geom)
    pk_list = sorted(polykeys)
    skipped = 0
    for i in range(0, len(pk_list), 100):
        chunk = pk_list[i:i + 100]
        inlist = ','.join(str(p) for p in chunk)
        rows = sda('SELECT mupolygonkey, mukey, mupolygongeo FROM '
                   'mupolygon WHERE mupolygonkey IN (%s)' % inlist)
        for (pk, mk, wkt) in rows:
            try:
                from shapely import from_wkt
                g = from_wkt(wkt)
            except Exception:
                skipped += 1
                continue
            geoms = list(g.geoms) if g.geom_type == 'MultiPolygon' \
                else [g]
            for gg in geoms:
                feats.append((int(mk), gg))
        print('  polygons chunk %d-%d: %d features so far'
              % (i, min(i + 100, len(pk_list)), len(feats)))
    print('raw mupolygon features: %d (skipped bad: %d)'
          % (len(feats), skipped))

    # ---- clip, simplify, dissolve by mukey (connected components) ----
    by_mukey = defaultdict(list)
    for mk, g in feats:
        try:
            c = g.intersection(corridor)
        except Exception:
            continue
        if c.is_empty:
            continue
        c = c.simplify(0.0008)  # ~70-90 m, as in build-soils.py
        if c.is_empty:
            continue
        geoms = list(c.geoms) if c.geom_type == 'MultiPolygon' else [c]
        by_mukey[mk].extend(geoms)
    print('mukeys with clipped geometry: %d' % len(by_mukey))

    out_feats = []
    unclassified = 0
    for mk, geoms in by_mukey.items():
        merged = unary_union(geoms)
        parts = list(merged.geoms) if merged.geom_type == 'MultiPolygon' \
            else [merged]
        a = attrs.get(mk, {})
        rating, rule, note = classify(a)
        if rule.startswith('UNCLASSIFIED'):
            unclassified += 1
        for pg in parts:
            if pg.is_empty:
                continue
            gkm = to_km_geom(pg)
            acres = round(gkm.area * 247.105, 1)
            county, region = county_of(pg)
            coords = [[[round(x, 4), round(y, 4)] for x, y in ring.coords]
                      for ring in [pg.exterior] + list(pg.interiors)]
            out_feats.append({
                'type': 'Feature',
                'properties': {
                    'mukey': mk,
                    'musym': a.get('musym'),
                    'muname': a.get('muname'),
                    'nrcs_rating': a.get('nrcs_rating'),
                    'nrcs_index': a.get('nrcs_index'),
                    'reasons': ([{'feature': k, 'index': v}
                                 for k, v in a.get('reasons', [])]
                                if a.get('reasons') else None),
                    'drainage': a.get('drainage'),
                    'hydric_major': a.get('hydric_major'),
                    'hydric_pct': a.get('hydric_pct'),
                    'histosol': bool(a.get('histosol')),
                    'slope': a.get('slope'),
                    'flood': a.get('flood'),
                    'pond': a.get('pond'),
                    'wtdepannmin_cm': a.get('wtdepannmin_cm'),
                    'rating': rating,
                    'rule': rule,
                    'note': note,
                    'acres': acres,
                    'county': county,
                    'region': region,
                    'source': 'NRCS SSURGO via Soil Data Access '
                              '(survey vintage varies by county; '
                              'tabular pull %s)' % TODAY,
                },
                'geometry': {'type': 'Polygon', 'coordinates': coords},
            })
    gj = {'type': 'FeatureCollection', 'features': out_feats}
    with open(OUT, 'w') as f:
        json.dump(gj, f, separators=(',', ':'))
    counts = Counter(feat['properties']['rating'] for feat in out_feats)
    rule_counts = Counter(feat['properties']['rule'].split(' + ')[0]
                          for feat in out_feats)
    print('WROTE %s: %d features, %d bytes'
          % (OUT, len(out_feats), os.path.getsize(OUT)))
    print('ratings:', dict(counts))
    print('first-rule counts:', dict(rule_counts))
    print('unclassified (no rating): %d' % unclassified)
    print('mukeys with cointerp reasons: %d of %d'
          % (len(reasons), len(by_mukey)))
    print('elapsed %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()

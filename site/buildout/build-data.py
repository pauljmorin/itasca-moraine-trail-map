#!/usr/bin/env python3
"""Build-out viewer v1 data build.
Converts the three Drive KML/KMZ drawn routes to GeoJSON, and cuts the
two gap surface GeoJSONs + Street View points from site/data/trail-minnesota.geojson.
Pure stdlib. Run from the repo root.
"""
import json, math, os, re, sys, zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'site', 'buildout', 'src')
OUT = os.path.join(ROOT, 'site', 'buildout', 'data')
os.makedirs(OUT, exist_ok=True)

R = 3958.7613  # earth radius in miles

def haversine_miles(coords):
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlmb = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
        total += 2 * R * math.asin(min(1.0, math.sqrt(a)))
    return total

def geom_length_miles(geom):
    t = geom['type']
    if t == 'LineString':
        return haversine_miles(geom['coordinates'])
    if t == 'MultiLineString':
        return sum(haversine_miles(c) for c in geom['coordinates'])
    if t == 'Polygon':
        return sum(haversine_miles(ring) for ring in geom['coordinates'])
    if t == 'MultiPolygon':
        return sum(sum(haversine_miles(ring) for ring in poly) for poly in geom['coordinates'])
    return 0.0

NS = {'k': 'http://www.opengis.net/kml/2.2'}

def parse_coords(text):
    pts = []
    for tok in text.split():
        parts = tok.split(',')
        if len(parts) >= 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                pass
    return pts

def kml_to_features(kml_bytes):
    root = ET.fromstring(kml_bytes)
    feats = []
    for pm in root.iter('{http://www.opengis.net/kml/2.2}Placemark'):
        name_el = pm.find('k:name', NS)
        name = name_el.text.strip() if name_el is not None and name_el.text else ''
        desc_el = pm.find('k:description', NS)
        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ''
        for ls in pm.findall('.//k:LineString', NS):
            c = ls.find('k:coordinates', NS)
            if c is not None and c.text:
                pts = parse_coords(c.text)
                if len(pts) >= 2:
                    feats.append({'type': 'Feature',
                                  'properties': {'name': name, 'description': desc},
                                  'geometry': {'type': 'LineString', 'coordinates': [[a, b] for a, b in pts]}})
        for pg in pm.findall('.//k:Polygon', NS):
            rings = []
            for ring_el in pg.findall('.//k:LinearRing', NS):
                c = ring_el.find('k:coordinates', NS)
                if c is not None and c.text:
                    pts = parse_coords(c.text)
                    if len(pts) >= 3:
                        rings.append([[a, b] for a, b in pts])
            if rings:
                feats.append({'type': 'Feature',
                              'properties': {'name': name, 'description': desc},
                              'geometry': {'type': 'Polygon', 'coordinates': rings}})
    return feats

def write_geojson(path, feats):
    with open(path, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': feats}, f)
    return path

def report(label, feats):
    total = sum(geom_length_miles(f['geometry']) for f in feats)
    print(f"{label}: {len(feats)} feature(s), {total:.2f} mi total")
    for f in feats:
        print(f"   - {f['properties'].get('name')!r}: {geom_length_miles(f['geometry']):.2f} mi")
    return total

# ---- 1. Proposed Arrowhead line (KML) ----
with open(os.path.join(SRC, 'proposed-arrowhead.kml'), 'rb') as f:
    feats = kml_to_features(f.read())
# drop any degenerate/junk features (e.g. single-point or absurd coords)
feats = [f for f in feats if all(-180 <= x <= -60 and 40 <= y <= 50
                                 for ring in ([f['geometry']['coordinates']] if f['geometry']['type'] == 'LineString' else f['geometry']['coordinates'])
                                 for x, y in ring)]
for f in feats:
    f['properties']['length_mi'] = round(geom_length_miles(f['geometry']), 2)
write_geojson(os.path.join(OUT, 'proposed-arrowhead.geojson'), feats)
report('proposed-arrowhead', feats)

# ---- 2. MWP chapter plan (KML) ----
with open(os.path.join(SRC, 'mwp-plan.kml'), 'rb') as f:
    feats = kml_to_features(f.read())
kept, dropped = [], []
for f in feats:
    coords = f['geometry']['coordinates'] if f['geometry']['type'] == 'LineString' else []
    junk = any(x > 0 or y < 0 for x, y in coords)  # junk coord at 115E, -60S
    (dropped if junk else kept).append(f)
for f in dropped:
    print(f"   DROPPED junk/broken: {f['properties'].get('name')!r}")
for f in kept:
    f['properties']['length_mi'] = round(geom_length_miles(f['geometry']), 2)
write_geojson(os.path.join(OUT, 'proposed-western.geojson'), kept)
report('proposed-western', kept)

# ---- 3. 2004 corridor (KMZ) ----
with zipfile.ZipFile(os.path.join(SRC, 'corridor-2004.kmz')) as z:
    names = z.namelist()
    print('KMZ contents:', names)
    kml_name = next(n for n in names if n.lower().endswith('.kml'))
    feats = kml_to_features(z.read(kml_name))
for f in feats:
    f['properties']['length_mi'] = round(geom_length_miles(f['geometry']), 2)
write_geojson(os.path.join(OUT, 'corridor-2004.geojson'), feats)
report('corridor-2004', feats)

# ---- 4/5. Gap surface cuts from the NCTA line ----
with open(os.path.join(ROOT, 'site', 'data', 'trail-minnesota.geojson')) as f:
    mn = json.load(f)['features']
print(f"trail-minnesota: {len(mn)} features")

SURF = {
    'Foot Path': ('foot', 'Foot tread (off-road)'),
    'Developed Path': ('paved', 'Paved multi-use path'),
    'Public Road': ('road', 'On-road walk'),
    'Sidewalk': ('sidewalk', 'Sidewalk'),
}
def classify(props):
    tt = props.get('trail_type')
    if tt in SURF:
        return SURF[tt]
    return ('other', 'Other / untyped')

def cut_gap(pred, label):
    out, totals = [], {}
    for f in mn:
        if not pred(f):
            continue
        code, lab = classify(f['properties'])
        p = dict(f['properties'])
        p['surface'] = code
        p['surface_label'] = lab
        g = {'type': 'Feature', 'properties': p, 'geometry': f['geometry']}
        out.append(g)
        totals[code] = totals.get(code, 0.0) + (p.get('len_miles') or geom_length_miles(f['geometry']))
    print(f"{label}: {len(out)} features, {sum(totals.values()):.2f} mi")
    for code in ('foot', 'paved', 'road', 'sidewalk', 'other'):
        if code in totals:
            print(f"   {code:9s} {totals[code]:7.2f} mi")
    return out

def in_bbox(f, lon0, lon1, lat0, lat1):
    g = f['geometry']
    coords = g['coordinates'] if g['type'] == 'LineString' else [c for line in g['coordinates'] for c in line]
    return any(lon0 <= x <= lon1 and lat0 <= y <= lat1 for x, y in coords)

def centroid_lon(f):
    g = f['geometry']
    cs = g['coordinates'] if g['type'] == 'LineString' else [c for line in g['coordinates'] for c in line]
    return sum(c[0] for c in cs) / len(cs)

# Arrowhead: bbox per research, chapters ARW + ELY only (KEK excluded).
# Drop the Hwy 6 road-walk feature west of Grand Rapids (centroid lon < -93.66):
# it belongs to the Hwy 6 -> Tioga Beach corridor, not GR->Ely.
arrow = cut_gap(lambda f: f['properties'].get('chapter') in ('ARW', 'ELY')
                and in_bbox(f, -93.66, -91.63, 47.15, 47.96)
                and centroid_lon(f) >= -93.66, 'gap-arrowhead')
write_geojson(os.path.join(OUT, 'gap-arrowhead.geojson'), arrow)

# Western: ALL of chapter MWP (Becker Co line at Frazee -> ND border) PLUS the
# four LLC 'Becker Co Line To NCT' connector features that join the MWP line at
# Frazee to the Becker County line. This is the clean auditable chain cut:
# 90 features, 104.86 mi, 78.38 mi on-road. The DL research file traces 113.63 mi
# / 78.82 mi on-road (91 features) — an 8.8-mi difference the research file does
# not reconcile from the same data (its off-road figure exceeds the chain cut by
# ~8.4 mi); flagged for the coordinator, NOT padded here.
west = cut_gap(lambda f: (f['properties'].get('chapter') == 'MWP')
               or (f['properties'].get('chapter') == 'LLC'
                   and f['properties'].get('seg_name') == 'Becker Co Line To NCT'),
               'gap-western')
write_geojson(os.path.join(OUT, 'gap-western.geojson'), west)

# ---- 6. Street View points ----
SV = [
    # GR-Ely (research §6)
    ('MN-135 just south of Tower', 'MN-135', 47.78552, -92.27775,
     'The last unfinished stretch of the Mesabi Trail — the trail still ends here; hikers walk MN-135.'),
    ('MN-135, Wahlsten area', 'MN-135', 47.68962, -92.28937,
     'The long, straight no-shoulder stretch hikers faced for ~15 mi before the trail was built — the "before" view.'),
    ('MN-135 at Embarrass', 'MN-135', 47.60198, -92.23610,
     'South end of the old Embarrass–Tower gap, where the trail dead-ended ~6 mi short of Tower.'),
    ('MN-169, Eagles Nest area', 'MN-169', 47.85725, -92.07404,
     'The contrast shot: rebuilt 2018 with 8-ft shoulders — what a rebuilt highway looks like.'),
    ('MN-169 / E. Sheridan St, Ely', 'MN-169', 47.90316, -91.85395,
     'East end of the Mesabi Trail, where the NCT continues east on Fernberg Rd toward Kawishiwi Falls.'),
    # Western (research §6)
    ('US-75 at Kent', 'US-75', 46.46138, -96.70734,
     'Two-lane US highway, 55 mph statutory default, narrow-to-no shoulder — the most exposed highway stretch on the western route.'),
    ('CR-88 southeast of Rothsay', 'CR-88', 46.469, -96.279,
     'Northwest end of the 15.8-mi CR-88 stretch; paved county road, farm traffic.'),
    ('CR-88 at Fergus Falls', 'CR-88', 46.306, -96.092,
     'Where the CR-88 road walk reaches town.'),
    ('US-59, Fergus Falls', 'US-59', 46.26468, -96.09495,
     'The route crosses I-94, US-59 and the Pelican River in close succession — the highest-traffic crossing on the corridor.'),
    ('MN-210 E, Fergus Falls', 'MN-210', 46.27081, -96.05075,
     'Trunk highway through east Fergus Falls; the Central Lakes Trail trailhead sits on Hwy 210.'),
    ('ND-4 / Fort Abercrombie', 'ND-4', 46.44715, -96.7239,
     'The Red River crossing: road-walk Minnesota meets off-road trail in North Dakota.'),
]
sv_feats = []
for name, road, lat, lon, why in SV:
    url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
    sv_feats.append({'type': 'Feature',
                     'properties': {'name': name, 'road': road, 'why': why,
                                    'url': url, 'verified': False},
                     'geometry': {'type': 'Point', 'coordinates': [lon, lat]}})
write_geojson(os.path.join(OUT, 'gap-streetview.geojson'), sv_feats)
print(f"gap-streetview: {len(sv_feats)} points (all verified:false)")
print('DONE')

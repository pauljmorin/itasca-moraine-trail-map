#!/usr/bin/env python3
"""Extend the Street View layer (Paul, Nov 18, 2026).

Two outputs:
1. Wires 6 already-verified gap Street View points
   (site/buildout/data/gap-streetview.geojson, verified by a browser
   check; pano dates Jun 2024-Sep 2025) into the main layer
   (site/data/streetview.geojson, 24 -> 30 features), converted to the
   main-layer schema. Headings are COMPUTED, not observed: the bearing
   of the road/trail line at the nearest point, in route-travel
   direction (stored coordinate order, verified south->north on
   MN-135 and NW->SE on CR-88; flipped eastward for the Ely point,
   where the Mesabi Trail pieces are stored in mixed order).
   trail_lat/trail_lon is the nearest point on that line.
   [JUDGMENT: the computed heading is a starting aim; the browser
   check that verifies a point should confirm or correct it.]
2. Derives the verification queue of candidate points that are NOT
   yet verified (site/buildout/data/streetview-candidates.geojson +
   docs/streetview-verification-queue-2026-11-18.md): western
   road-walk segment endpoints, Arrowhead road-piece endpoints, and
   ITM trail/road crossings without coverage. These are NOT added to
   the main layer: every new point needs a browser check that Google
   Street View imagery actually exists there (the Nov 13 method:
   open the pano URL, confirm imagery, record imagery date and the
   heading that shows the trail). A candidate that fails the check
   stays out, like the 8 of 19 that failed on Nov 13 and the
   ND-4 / Fort Abercrombie point (verified False, no pano on the
   highway) in the gap file.

Dedupe radius against existing coverage (main layer + the 6 wired
points): 150 m. Excluded from the queue: points within 150 m of
existing coverage, and the 5 gap points that are documentary
safety-case viewpoints off the trail line (MN-169 Eagles Nest,
US-75 Kent, US-59 Fergus Falls, MN-210 E Fergus Falls) plus ND-4
(no imagery) — all listed in SOURCES.md.
"""
import json, math, re
from collections import Counter, defaultdict

REPO = '/home/hatch/workspace/itasca-trail-map'

def load(p):
    with open(p) as f:
        return json.load(f)

def hav_m(a, b):
    R = 6371000
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp = p2 - p1
    dl = math.radians(b[0] - a[0])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def bearing(a, b):
    """Degrees clockwise from north, a/b = (lon, lat)."""
    dlon = math.radians(b[0] - a[0])
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def parse_viewpoint(url):
    m = re.search(r'viewpoint=(-?[\d.]+),(-?[\d.]+)', url)
    lat, lon = float(m.group(1)), float(m.group(2))
    return lat, lon

# ---------------------------------------------------------------- data
sv = load(f'{REPO}/site/data/streetview.geojson')
gap = load(f'{REPO}/site/buildout/data/gap-streetview.geojson')['features']
rw = load(f'{REPO}/site/data/roadwalk.geojson')['features']
gap_arw = load(f'{REPO}/site/buildout/data/gap-arrowhead.geojson')['features']
ap = load(f'{REPO}/site/data/access-points.geojson')['features']
tmn = load(f'{REPO}/site/data/trail-minnesota.geojson')['features']

from shapely.geometry import shape, Point, LineString
from shapely.ops import nearest_points

WIRE = ['MN-135 just south of Tower', 'MN-135, Wahlsten area',
        'MN-135 at Embarrass', 'MN-169 / E. Sheridan St, Ely',
        'CR-88 southeast of Rothsay', 'CR-88 at Fergus Falls']

# Lines used for heading / trail-point computation.
# (label, shapely line) — stored order = route-travel direction,
# verified for the MN-135 road pieces (S->N) and CR-88 (NW->SE).
arw_road_lines = [shape(f['geometry']) for f in gap_arw
                  if f['properties'].get('surface') == 'road']
arw_paved_lines = [shape(f['geometry']) for f in gap_arw
                   if f['properties'].get('surface') == 'paved']
west_lines = [(f['properties']['segment'], shape(f['geometry'])) for f in rw
              if f['properties'].get('area') == 'western'
              and f['properties'].get('kind') == 'line']

def nearest_on(lines, pt):
    """(line, nearest point on it, distance m) for the closest line."""
    best = None
    for ln in lines:
        np_ = nearest_points(pt, ln)[1]
        d = hav_m((pt.x, pt.y), (np_.x, np_.y))
        if best is None or d < best[2]:
            best = (ln, np_, d)
    return best

def heading_along(line, pt, flip_if_west=False):
    """Bearing of the line at the vertex nearest pt, in stored order.
    If flip_if_west, reverse it when it points west (decreasing lon)."""
    coords = list(line.coords)
    # nearest vertex
    vi = min(range(len(coords)),
             key=lambda i: hav_m((pt.x, pt.y), coords[i]))
    if vi == 0:
        a, b = coords[0], coords[1]
    elif vi == len(coords) - 1:
        a, b = coords[-2], coords[-1]
    else:
        a, b = coords[vi], coords[vi + 1]
    h = bearing(a, b)
    if flip_if_west and b[0] < a[0]:
        h = (h + 180) % 360
    return round(h)

FACES = {
    'MN-135 just south of Tower': 'the road walk on MN-135 toward Tower',
    'MN-135, Wahlsten area': 'the road walk on MN-135',
    'MN-135 at Embarrass': 'the road walk on MN-135 toward Tower',
    'MN-169 / E. Sheridan St, Ely': 'the trail leaving the Mesabi Trail for Fernberg Rd',
    'CR-88 southeast of Rothsay': 'the road walk on CR-88 toward Fergus Falls',
    'CR-88 at Fergus Falls': 'the road walk on CR-88 into Fergus Falls',
}

# ---------------------------------------------------------------- 1. wire the 6 verified gap points
wired = []
for g in gap:
    name = g['properties']['name']
    if name not in WIRE:
        continue
    p = g['properties']
    lat, lon = parse_viewpoint(p['url'])
    pt = Point(lon, lat)
    if 'MN-135' in name:
        ln, tp, _ = nearest_on(arw_road_lines, pt)
        h = heading_along(ln, tp)
    elif 'Ely' in name:
        ln, tp, _ = nearest_on(arw_paved_lines, pt)
        h = heading_along(ln, tp, flip_if_west=True)
    else:  # CR-88
        ln, tp, _ = nearest_on([g2 for _, g2 in west_lines], pt)
        h = heading_along(ln, tp)
    wired.append({
        'type': 'Feature',
        'geometry': {'coordinates': [lon, lat], 'type': 'Point'},
        'properties': {
            'faces': FACES[name],
            'heading': h,
            'imagery': p['pano_date'],
            'name': name,
            'pano_lat': lat,
            'pano_lon': lon,
            'photosphere': False,
            'trail_lat': round(tp.y, 5),
            'trail_lon': round(tp.x, 5),
            'url': ('https://www.google.com/maps/@?api=1&map_action=pano'
                    f'&viewpoint={lat:.5f},{lon:.5f}&heading={h}&pitch=0'),
            # provenance, carried from the gap file (popup ignores them)
            'road': p['road'],
            'why': p['why'],
            'pano_note': p['pano_note'],
            'verified': True,
        },
    })

orig_n = len(sv['features'])
sv['features'].extend(wired)
with open(f'{REPO}/site/data/streetview.geojson', 'w') as f:
    json.dump(sv, f, separators=(',', ':'))
print(f'main layer: {orig_n} -> {len(sv["features"])} features (+{len(wired)} wired)')
for w in wired:
    pr = w['properties']
    print(f"  {pr['name']}: heading {pr['heading']} imagery {pr['imagery']}")

# ---------------------------------------------------------------- 2. candidate queue
cover = [(f['geometry']['coordinates'][1], f['geometry']['coordinates'][0])
         for f in sv['features']]
def nearest_cover_m(lat, lon):
    return min(hav_m((lon, lat), (clon, clat)) for clat, clon in cover)

SEG_ROAD = {}
for f in rw:
    if f['properties'].get('kind') == 'speed':
        SEG_ROAD[f['properties']['segment']] = (
            f['properties'].get('road'), f['properties'].get('miles'))

cands = []
def short_label(name):
    # "Seg 1 end — ..." -> "Seg 1 end"; "Trail crossing — X (Chip-6)" -> "(Chip-6)"
    if name.startswith('Seg '):
        return name.split(' — ')[0]
    m = re.search(r'(\(Chip-\d+\))$', name)
    return m.group(1) if m else name

def add_cand(kind, priority, name, lat, lon, why, heading, note=''):
    if nearest_cover_m(lat, lon) <= 150:
        return 'covered'
    for c in cands:
        clon, clat = c['geometry']['coordinates']
        if hav_m((lon, lat), (clon, clat)) <= 150:
            # same physical point derived twice (e.g. Seg 1 end == Seg 2
            # start, or one crossing serving two segments): merge labels
            c['properties']['name'] += ' / ' + short_label(name)
            c['properties']['priority'] = min(c['properties']['priority'], priority)
            if note:
                prev = c['properties'].get('note', '')
                c['properties']['note'] = (prev + ' ' + note).strip() if prev else note
            return 'merged'
    cands.append({
        'type': 'Feature',
        'geometry': {'coordinates': [round(lon, 5), round(lat, 5)], 'type': 'Point'},
        'properties': {
            'kind': kind, 'priority': priority, 'name': name,
            'why': why, 'heading_suggested': heading,
            'nearest_existing_sv_m': round(nearest_cover_m(lat, lon)),
            'note': note,
            'pano_url': ('https://www.google.com/maps/@?api=1&map_action=pano'
                         f'&viewpoint={lat:.5f},{lon:.5f}&pitch=0'),
            'verified': False,
        },
    })
    return 'added'

# --- western road-walk segment endpoints ---
by_seg = defaultdict(list)
for f in rw:
    if f['properties'].get('area') == 'western' and f['properties'].get('kind') == 'line':
        by_seg[f['properties']['segment']].append(shape(f['geometry']))
def seg_num(s):
    return int(s.split()[1])

# Chain the segments in mile order (Seg 1 -> Seg 15). A segment's
# start is the candidate end nearest the previous segment's end;
# its end is the candidate farthest from that start. (Longitude
# alone mislabels north-south segments such as Seg 10, which runs
# north along CSAH 3.) Remaining singleton candidates are interior
# line breaks in the roadwalk data.
prev_end = None
for seg in sorted(by_seg, key=seg_num):
    lines = by_seg[seg]
    ends = Counter()
    for ln in lines:
        c = list(ln.coords)
        ends[tuple(c[0])] += 1
        ends[tuple(c[-1])] += 1
    clusters = []
    for c, n in ends.items():
        hit = None
        for cl in clusters:
            if hav_m(c, cl[0]) < 40:
                hit = cl
                break
        if hit is None:
            clusters.append([c, n])
        else:
            hit[1] += n
    road, miles = SEG_ROAD.get(seg, ('', ''))
    # candidate ends: singletons, plus the longitude extremes (a true
    # end can carry count 2 where two pieces overlap there, e.g. Seg 12)
    ordered = sorted(clusters, key=lambda cl: cl[0][0])
    cand_idx = {i for i, (c, n) in enumerate(clusters)
                if n == 1 or c == ordered[0][0] or c == ordered[-1][0]}
    cands_xy = [clusters[i][0] for i in sorted(cand_idx)]
    if prev_end is None:
        start_c = min(cands_xy, key=lambda c: c[0])  # Seg 1: westernmost
    else:
        start_c = min(cands_xy, key=lambda c: hav_m(c, prev_end))
    end_c = max((c for c in cands_xy if c != start_c),
                key=lambda c: hav_m(c, start_c))
    for c in cands_xy:
        lon, lat = c
        if c == start_c:
            tag, prio, note = 'start', 1, ''
        elif c == end_c:
            tag, prio, note = 'end', 1, ''
        else:
            tag = 'line break in roadwalk data'
            note = ('Interior break in the roadwalk line pieces: confirm on the map '
                    'whether this is a real trail on/off point or a data gap.')
            prio = 3
        # suggested heading: tangent in travel direction at this end
        ln, tp, _ = nearest_on(lines, Point(lon, lat))
        h = heading_along(ln, tp)
        add_cand('roadwalk-endpoint', prio,
                 f'{seg} {tag} — {road} ({miles})', lat, lon,
                 f'Western road-walk {seg}: trail gets {"on" if tag == "start" else "off"} the road here.',
                 h, note)
    prev_end = end_c

# --- Arrowhead road-piece endpoints ---
arw_lines = [shape(f['geometry']) for f in rw
             if f['properties'].get('area') == 'arrowhead'
             and f['properties'].get('kind') == 'line']
ends = Counter()
for ln in arw_lines:
    c = list(ln.coords)
    ends[tuple(c[0])] += 1
    ends[tuple(c[-1])] += 1
clusters = []
for c, n in ends.items():
    hit = None
    for cl in clusters:
        if hav_m(c, cl[0]) < 40:
            hit = cl
            break
    if hit is None:
        clusters.append([c, n])
    else:
        hit[1] += n
# Only chain ends (seen once) are trail on/off points; a cluster seen
# twice is an interior joint between two pieces of the same road walk.
for c, n in clusters:
    if n != 1:
        continue
    lon, lat = c
    area = ('Grand Rapids area' if lon < -93.0 else
            'Tower area' if lon < -92.0 else 'Ely area')
    ln, tp, _ = nearest_on(arw_lines, Point(lon, lat))
    h = heading_along(ln, tp)
    add_cand('roadwalk-endpoint', 1,
             f'Arrowhead road-walk piece end — {area}', lat, lon,
             'Arrowhead road-walk piece ends here; trail gets on/off the road.',
             h)

# --- ITM trail/road crossings without coverage ---
trail_lines = [shape(f['geometry']) for f in tmn]
for f in ap:
    if f['properties'].get('kind') != 'road':
        continue
    lon, lat = f['geometry']['coordinates']
    label = f['properties'].get('label')
    for_name = f['properties'].get('for_name')
    pt = Point(lon, lat)
    ln, tp, _ = nearest_on(trail_lines, pt)
    h = heading_along(ln, tp, flip_if_west=True)
    add_cand('trail-road-crossing', 2,
             f'Trail crossing — {label} ({for_name})', lat, lon,
             'ITM foot trail crosses this road; hikers get on/off here.',
             h)

with open(f'{REPO}/site/buildout/data/streetview-candidates.geojson', 'w') as f:
    json.dump({'type': 'FeatureCollection', 'features': cands}, f, indent=1)
print(f'queue: {len(cands)} candidates')
print('  by kind:', Counter(c['properties']['kind'] for c in cands))
print('  by priority:', Counter(c['properties']['priority'] for c in cands))

# --- queue doc ---
lines = ['# Street View verification queue — 2026-11-18',
         '',
         'Candidates derived from the road-walk and access data for the main',
         'Street View layer. NONE of these is verified: each needs the Nov 13',
         'browser check (open the pano URL, confirm Google Street View imagery',
         'exists, record the imagery date and the heading that shows the trail).',
         'A candidate that fails the check stays out. Do not add unverified',
         'points to `site/data/streetview.geojson`.',
         '',
         '| # | Point | Type | Prio | Lat, Lon | Nearest existing SV | Suggested heading |',
         '|---|-------|------|------|----------|---------------------|-------------------|']
for i, c in enumerate(sorted(cands, key=lambda x: (x['properties']['priority'],
                                                   x['properties']['name'])), 1):
    pr = c['properties']
    lon, lat = c['geometry']['coordinates']
    lines.append(f"| {i} | {pr['name']} | {pr['kind']} | {pr['priority']} | "
                 f"{lat:.5f}, {lon:.5f} | {pr['nearest_existing_sv_m']:,} m | "
                 f"{pr['heading_suggested']} |")
lines += ['',
          'Pano URL for each candidate (open in a browser, confirm imagery):',
          '']
for i, c in enumerate(sorted(cands, key=lambda x: (x['properties']['priority'],
                                                   x['properties']['name'])), 1):
    pr = c['properties']
    lines.append(f"{i}. {pr['name']}: {pr['pano_url']}")
    if pr['note']:
        lines.append(f"   Note: {pr['note']}")
lines += ['',
          'Priority: 1 = road-walk segment end (trail on/off the road), '
          '2 = ITM trail/road crossing, 3 = interior line break in the '
          'roadwalk data (confirm it is a real on/off point first).',
          '',
          'Already checked and excluded (do not re-queue): ND-4 / Fort '
          'Abercrombie (verified False — no pano on the highway; nearest pano '
          'is inside the historic-site grounds); MN-169 Eagles Nest, US-75 '
          'Kent, US-59 Fergus Falls, MN-210 E Fergus Falls (verified, but '
          'documentary safety-case viewpoints 0.6–2.2 km off the trail line, '
          'not intersections or access points).']
with open(f'{REPO}/docs/streetview-verification-queue-2026-11-18.md', 'w') as f:
    f.write('\n'.join(lines) + '\n')
print('queue doc written')

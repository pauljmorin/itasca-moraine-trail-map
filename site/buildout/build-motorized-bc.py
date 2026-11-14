#!/usr/bin/env python3
"""Build the Brainerd-to-Canada ATV layer for the Finishing the Trail
build-out viewer (planning mode).

Sources (all live, Nov 13, 2026):
- Minnesota DNR OHV Trails, 2026 season — ArcGIS REST FeatureServer
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0
  (the same DNR service the Arrowhead motorized layers use; it is the
  authoritative GIS for the designated trails, and the DNR GeoPDFs render
  from the same data. GeoPDFs were NOT used as the geometry source: this VM
  has no GDAL/OGR or PDF tooling to convert them, so per the build rule they
  were not forced — the FeatureServer supplies the same DNR geometries.)
- Inventory / published mileages / honest lines:
  docs/gap-atv-brainerd-canada-inventory.csv and
  docs/gap-atv-brainerd-canada-research.md.

What this layer is and is not:
- It draws the designated ATV systems of the wider Brainerd->Canada
  corridor that are NOT already drawn on the Arrowhead ATV layer
  (motorized-atv.geojson, clipped to 2 mi around the proposed Arrowhead
  line / 2004 corridor). Systems already drawn there are NOT re-added;
  the panel table marks them "Drawn (Arrowhead)".
- Geometries are drawn WHOLE (no clip buffer): the point of this layer is
  the full Brainerd-to-Canada corridor, not the Arrowhead clip.
- Service trail names differ from CSV names ("ATV" inserted mid-name,
  "Bigfork" vs "Big Fork", county splits as separate rows). SERVICE_MAP
  below is the verified mapping, checked against the service Nov 13, 2026.

Outputs:
- site/buildout/data/motorized-atv-bc.geojson — the new layer.
- site/buildout/src/motorized-bc-stats.json — counts, GIS-measured miles,
  per-system rollup, drawn flags.
- Injects the Brainerd-to-Canada planning section into
  site/buildout/index.html between BRAINERD-CANADA-SECTION markers.

Totals shown respect the research file's own cautions and are never added
across categories: designated 1,630.5 (ATV-only 1,599.5) is an arithmetic
sum of published system mileages, not a surveyed network length; club-system
miles (Voyageur Country ~250, Northwoods Alliance 500+) overlap the
designated figures and are NOT additive; the 101,417-mi "everything
rideable" figure is a different universe and is not used.

Writes build log lines to stdout; exits non-zero on any failure.
"""
import csv, json, math, os, re, sys, urllib.request, urllib.parse

from shapely.geometry import shape, mapping, LineString, MultiLineString
from shapely.ops import unary_union
from pyproj import Transformer

BASE = os.path.dirname(os.path.abspath(__file__))  # site/buildout
DATA = os.path.join(BASE, 'data')
SRC = os.path.join(BASE, 'src')
REPO = os.path.dirname(os.path.dirname(BASE))  # repo root
UA = {'User-Agent': 'Mozilla/5.0 (build-out viewer data pull)'}

OHV_FS = ('https://enterprise.gisdata.mn.gov/aghost/rest/services/'
          'us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0')
# Brainerd -> Canada corridor envelope (lon/lat).
ENV = {'xmin': -95.3, 'ymin': 46.2, 'xmax': -89.3, 'ymax': 48.7,
       'spatialReference': {'wkid': 4326}}

TO4326 = Transformer.from_crs('EPSG:26915', 'EPSG:4326', always_xy=True)
TOUTM = Transformer.from_crs('EPSG:4326', 'EPSG:26915', always_xy=True)
MI = 1609.34

# DNR service trail_name -> CSV system name. Verified against the live
# service Nov 13, 2026 (probe: 6,211 features, 82 distinct names in ENV).
SERVICE_MAP = {
    'Crow Wing Southern Loop': 'Crow Wing Southern Loop',
    'Fort Ripley Trails': 'Fort Ripley Trail and Ripley Connection',
    'Miller-Black Bear Trail': 'Miller-Black Bear',
    'Miller Hills OHM Trail': 'Miller Hills (OHM only)',
    "Mississippi River Northwood's Trail": 'Mississippi River Northwoods',
    'Pine Center Trail': 'Pine Center Trails',
    'Emily- Blind Lake: Aitkin County': 'Emily–Blind Lake Trail',
    'Emily/Outing Trail': 'Emily-Outing Trail',
    'Moose River Trail': 'Moose River Trail',
    'Soo Line North: Cass': 'Soo Line North Trail (Cass County)',
    'Spider Lake Trails': 'Spider Lake Trails',
    'Blind Lake Connector Trail': 'Blind Lake Connector and Loop',
    'Blind Lake Loop Trail': 'Blind Lake Connector and Loop',
    'Soo Line North: Aitkin': 'Soo Line North Trail (Aitkin County)',
    'Moose River Connector': 'Moose River Connector',
    'Axtell Technical Riding Area': 'Axtell Technical Riding Area',
    'Alvwood/Squaw Lake Trail': 'Alvwood–Squaw Lake ATV/OHM Trail',
    'Wilderness Trail': 'Wilderness Trail',
    'Thistledew Trail': 'Thistledew Trails',
    'UPM/Blandin Trail': 'UPM Blandin Trail',
    'Goodland Trail': 'Goodland ATV/OHM Trail',
    'Rabey Line Trail': 'Rabey Line and Hill City Connector',
    'Hill City Trail': 'Rabey Line and Hill City Connector',
    'Balsam Trail': 'Balsam Trail',
    'Blue Ox Trail(North of Funkley) (2A) MS84.029': 'Blue Ox Trail',
    'Blue Ox Trail (1A) MS84.029': 'Blue Ox Trail',
    'Voyageur Country ATV': 'Voyageur Country ATV Trail',
    'Stony Spur II': 'Stony Spur II Trail',
    'Turkey Time Trail': 'Turkey Time Trail',
    'Red Dot Trail': 'Red Dot Trail',
    'Wild Country Trail': 'Wild Country Trail',
    'Moose Walk Trail': 'Moose Walk Trail',
    'Moose Run Trail': 'Moose Run Trail',
    'Alger Grade OHM Trail': 'Alger Grade OHM Trail (OHM only)',
    'Old Greenwood Loop': 'Old Greenwood Trail',
    'Timber Frear Loop': 'Timber Frear Loop',
    'Hovland Woods Trail': 'Hovland Woods Trail',
    'Rice Lake Pancore Loop': 'Rice Lake Pancore Loop',
}

# Service names already drawn on the Arrowhead ATV layer
# (motorized-atv.geojson) — NOT re-added here.
ALREADY_DRAWN = {
    'Prospectors', 'Quad Cities Trail',
    'Iron Range OHV State Recreation Area, East Unit',
    'Iron Range OHV State Recreation Area, West Unit',
    'Chisholm Trail', 'East Range Multi-Use OHV Trail', 'Genoa Trail',
    'Herb Brandstrom Trail', 'Hibbing to Alborn', 'Len Hardy Memorial Trail',
    'Little Moose Trail', 'Mesabi Mountain Trail',
    'Taconite--Big Aspen Connection',
    'David Dill - Taconite State Trail (Ely to Purvis Area)',
    'Alborn-Pengilly Railroad State Trail MS84.029',
    'Big Fork and Balsam (B&B) Connection Trail',
}
# CSV names of the already-drawn systems (for the panel table).
ALREADY_DRAWN_CSV = {
    'Prospectors Trail (Prospector Loop)', 'Quad Cities ATV Trail',
    'Iron Range OHV State Recreation Area - East Unit',
    'Iron Range OHV State Recreation Area - West Unit',
    'Chisholm Trail', 'East Range Multi-Use Trail', 'Genoa Trail',
    'Herb Brandstrom ATV/OHM Trail', 'Hibbing to Alborn Trail',
    'Len Hardy Trail', 'Little Moose Trail', 'Mesabi Mountain Trail (ORV only)',
    'Taconite State Trail - Big Aspen Connection',
    'David Dill/Taconite State Trail - Ely to Purvis Area',
    'Alborn–Pengilly Railroad ATV Trail',
    'Bigfork and Balsam Connection',
}
# Already drawn, but only the 2-mi Arrowhead clip of the full system.
CLIPPED_ONLY = {'Alborn–Pengilly Railroad ATV Trail',
                'Bigfork and Balsam Connection'}

# CSV rows drawn on neither layer, with the honest reason.
LIST_ONLY_REASON = {
    'Jackpot Trail': 'No geometry in the DNR OHV service; DNR GeoPDF exists but could not be converted on this VM (no GDAL). DNR GeoPDF says 60-mi loop vs A-Z 30 — unresolved.',
    'Moose Trail (Biwabik-Skibo)': 'Not in the DNR A-Z listing and no geometry in the DNR OHV service.',
    'Seven Beaver ATV Trail (Skibo-Hwy 2)': 'Not in the DNR A-Z listing and no geometry in the DNR OHV service.',
    'C.J. Ramstad / North Shore State Trail (ATV segment)': 'No geometry in the DNR OHV service for the 7-mi ATV segment.',
    'B&B Connection (no DNR A-Z row found; EXCLUDED from corridor total)':
        'Excluded from the corridor total — no DNR A-Z row. The DNR service carries one trail under the '
        '"Big Fork and Balsam (B&B) Connection" name, already drawn on the Arrowhead layer; whether the '
        '32-mi A-Z row and this 33-mi county row are the same trail is research gap #1 — not merged here.',
    'Blue Ox Connection ATV Trail (PROPOSED)': 'Proposed, not built — LCCMR 2027 proposal 2027-552, not funded.',
    'Voyageur Country ATV Trail Phase 2 (PROPOSED)': 'Proposed, not built — EAW record of decision Apr 11, 2025 (negative, no EIS); permitting stage.',
}

FLAGS = {
    'Miller Hills (OHM only)': 'OHM only, not ATV — counted in the 1,630.5 total per the A-Z convention, excluded from the 1,599.5 ATV-only figure.',
    'Alger Grade OHM Trail (OHM only)': 'OHM only, not ATV — counted in the 1,630.5 total per the A-Z convention, excluded from the 1,599.5 ATV-only figure.',
    'Mesabi Mountain Trail (ORV only)': 'ORV only, not ATV — counted in the 1,630.5 total per the A-Z convention, excluded from the 1,599.5 ATV-only figure.',
    'Fort Ripley Trail and Ripley Connection': 'Maintainer disputed: DNR detail page names Central Lakes ATV Club; DNR GeoPDF credits Balsam Trail Blazers.',
    'Miller-Black Bear': 'DNR A-Z says 31 mi; Explore Minnesota describes a 20-mile network. DNR is authoritative.',
    'Mississippi River Northwoods': '11.5 mi per the DNR detail page and the county designation record; the A-Z table rounds to 11.',
    'Alborn–Pengilly Railroad ATV Trail': 'Managed-mileage split unresolved: Range Riders 9 vs 17 mi; East Range Riders vs Alborn Dirt Devils. The 39-mi total is stable.',
    'Bigfork and Balsam Connection': 'Drawn on the Arrowhead layer, clipped to the 2-mi buffer — most of the system is outside that clip.',
    'Blue Ox Trail': 'DNR A-Z lists the county as Koochiching only; the actual split is Beltrami 23 / Itasca 11 / Koochiching 40.',
    'Voyageur Country ATV Trail': 'Designated 36 mi vs a ~250-mi club system of signed corridor routes — different things. Phase 2 proposes up to 125 mi total (39 existing + 78 improved + 8 new), EAW stage. DNR service geometry measures 116.5 mi under this name — the service appears to include signed connector routes beyond the 36 designated miles.',
    'Stony Spur II Trail': 'DNR service geometry measures 58.9 mi — the DNR GeoPDF labels the Stony Spur II + Jackpot loop as 60 miles, so the service geometry is likely the combined loop; the A-Z 30 is used.',
    'Prospectors Trail (Prospector Loop)': 'Mileage disputed: DNR 167 mi; club 216+ mi; consultant 250 mi.',
    'Soo Line North Trail (Cass County)': 'County split Cass 52 + Aitkin 48 + Carlton 15 = 115 mi, 2 mi over the TrailLink figure — unresolved.',
    'Rabey Line and Hill City Connector': 'County page only in the research (no DNR GeoPDF found) — but the DNR service carries both the Rabey Line and Hill City Trail, so it is drawn here from the service.',
}

# Panel order: (heading, [CSV names in order]).
TABLES = [
    ('Crow Wing County — 186.5 mi, 7 designated trails',
     ['Crow Wing Southern Loop', 'Fort Ripley Trail and Ripley Connection',
      'Miller-Black Bear', 'Miller Hills (OHM only)',
      'Mississippi River Northwoods', 'Pine Center Trails',
      'Emily–Blind Lake Trail']),
    ('Cass County — 166 mi, 4 designated trails',
     ['Emily-Outing Trail', 'Moose River Trail',
      'Soo Line North Trail (Cass County)', 'Spider Lake Trails']),
    ('Aitkin County (southern feeder) — 89.5 mi',
     ['Blind Lake Connector and Loop',
      'Soo Line North Trail (Aitkin County)', 'Moose River Connector',
      'Axtell Technical Riding Area']),
    ('Itasca County — 420.5 mi, 12 trails',
     ['Alvwood–Squaw Lake ATV/OHM Trail', 'Wilderness Trail',
      'Alborn–Pengilly Railroad ATV Trail', 'Bigfork and Balsam Connection',
      'Thistledew Trails', 'UPM Blandin Trail', 'Goodland ATV/OHM Trail',
      'Rabey Line and Hill City Connector', 'Little Moose Trail',
      'Herb Brandstrom ATV/OHM Trail', 'Len Hardy Trail', 'Balsam Trail',
      'B&B Connection (no DNR A-Z row found; EXCLUDED from corridor total)']),
    ('Blue Ox Trail — 74 mi, the spine to the north',
     ['Blue Ox Trail']),
    ('Voyageur Country — 36 designated miles',
     ['Voyageur Country ATV Trail']),
    ('St. Louis County — 465 mi (corrected)',
     ['Prospectors Trail (Prospector Loop)', 'Quad Cities ATV Trail',
      'David Dill/Taconite State Trail - Ely to Purvis Area',
      'Taconite State Trail - Big Aspen Connection',
      'Iron Range OHV State Recreation Area - West Unit',
      'Iron Range OHV State Recreation Area - East Unit',
      'Chisholm Trail', 'East Range Multi-Use Trail', 'Jackpot Trail',
      'Stony Spur II Trail', 'Turkey Time Trail', 'Hibbing to Alborn Trail',
      'Genoa Trail', 'Mesabi Mountain Trail (ORV only)',
      'Moose Trail (Biwabik-Skibo)', 'Seven Beaver ATV Trail (Skibo-Hwy 2)']),
    ('Lake County — 114 mi (101 ATV + 13 OHM-only)',
     ['Red Dot Trail', 'Wild Country Trail', 'Moose Walk Trail',
      'Moose Run Trail',
      'C.J. Ramstad / North Shore State Trail (ATV segment)',
      'Alger Grade OHM Trail (OHM only)']),
    ('Cook County (eastern / Gunflint approach) — 79 mi',
     ['Old Greenwood Trail', 'Timber Frear Loop', 'Hovland Woods Trail',
      'Rice Lake Pancore Loop']),
]
PROPOSED = ['Blue Ox Connection ATV Trail (PROPOSED)',
            'Voyageur Country ATV Trail Phase 2 (PROPOSED)']
ADJACENT = ['Kelliher ATV Trail (adjacent)', 'Timber Trails (adjacent)',
            'Wilton Trails Northwest (adjacent)',
            'Fourtown-Grygla Trail (adjacent)',
            'Consolidated Conservation Trails (adjacent)',
            'Forest Riders Trail (adjacent)',
            'Round River Drive Trail (adjacent)',
            'Martineau Recreational Trails (adjacent; OHM only)',
            'Schoolcraft Trail (adjacent)',
            'Lake of the Woods Connector Trail (adjacent)',
            'Warroad/Roseau Trails (adjacent)',
            'Bemis Hill Trails (adjacent)',
            'Soo Line North Trail (Carlton County) (adjacent)']


def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8'))


def query_ids():
    params = {'where': '1=1', 'geometry': json.dumps(ENV),
              'geometryType': 'esriGeometryEnvelope',
              'spatialRel': 'esriSpatialRelIntersects',
              'returnIdsOnly': 'true', 'f': 'json'}
    url = OHV_FS + '/query?' + urllib.parse.urlencode(params)
    return fetch_json(url).get('objectIds', [])


def arcgis_geom_to_shapely(g):
    paths = g.get('paths', [])
    lines = []
    for p in paths:
        if len(p) >= 2:
            lines.append(LineString([(c[0], c[1]) for c in p]))
    if not lines:
        return None
    if len(lines) == 1:
        return lines[0]
    return MultiLineString(lines)


def project(geom, tr):
    if geom.geom_type == 'LineString':
        return LineString([tr.transform(x, y) for x, y in geom.coords])
    if geom.geom_type == 'MultiLineString':
        return MultiLineString([project(g, tr) for g in geom.geoms])
    raise ValueError('unsupported ' + geom.geom_type)


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def main():
    # ---- inventory ----
    csv_path = os.path.join(REPO, 'docs', 'gap-atv-brainerd-canada-inventory.csv')
    by_name = {}
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            by_name[row['name']] = row
    print('BC CSV rows: %d' % len(by_name))

    # ---- service: names first, geometry only for matched systems ----
    ids = query_ids()
    print('OHV features in BC envelope: %d' % len(ids))
    name_by_id = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {'objectIds': ','.join(str(x) for x in chunk),
                  'outFields': 'objectid,trail_name', 'returnGeometry': 'false', 'f': 'json'}
        d = fetch_json(OHV_FS + '/query?' + urllib.parse.urlencode(params))
        for feat in d.get('features', []):
            name_by_id[feat['attributes']['objectid']] = (
                feat['attributes'].get('trail_name') or 'Unnamed').strip()
    wanted_ids = [oid for oid, n in name_by_id.items() if n in SERVICE_MAP]
    print('features for the %d BC systems: %d' % (len(SERVICE_MAP), len(wanted_ids)))

    ohv_fields = ['objectid', 'trail_name', 'segment_name', 'surface_type',
                  'funding_type', 'trail_width', 'atv_class_1', 'atv_class_2',
                  'off_highway_motorcycle', 'off_road_vehicle', 'road_class',
                  'miles', 'web_site', 'program_project']
    recs = []
    for i in range(0, len(wanted_ids), 500):
        chunk = wanted_ids[i:i + 500]
        params = {'objectIds': ','.join(str(x) for x in chunk),
                  'outFields': ','.join(ohv_fields),
                  'outSR': '4326', 'returnGeometry': 'true', 'f': 'json'}
        d = fetch_json(OHV_FS + '/query?' + urllib.parse.urlencode(params))
        for feat in d.get('features', []):
            g = arcgis_geom_to_shapely(feat.get('geometry') or {})
            if g is None or g.is_empty:
                continue
            recs.append({'attrs': feat.get('attributes') or {}, 'geom4326': g})
    print('BC records with geometry: %d' % len(recs))

    # ---- per-system GIS miles (UTM) ----
    gis_mi = {}
    for r in recs:
        csv_name = SERVICE_MAP[(r['attrs'].get('trail_name') or '').strip()]
        g = project(r['geom4326'], TOUTM)
        gis_mi[csv_name] = gis_mi.get(csv_name, 0.0) + g.length / MI
    for n, v in sorted(gis_mi.items(), key=lambda kv: -kv[1]):
        pub = by_name[n]['miles']
        print('  GIS %-45s %7.1f mi (published %s)' % (n[:45], v, pub))

    # ---- build the viewer GeoJSON (whole systems, ~30 m simplify) ----
    out = []
    for r in recs:
        g = project(r['geom4326'], TOUTM).simplify(30)
        if g.is_empty:
            continue
        c4326 = project(g, TO4326)
        geoms = list(c4326.geoms) if c4326.geom_type == 'MultiLineString' else [c4326]
        coords = []
        for ln in geoms:
            coords.append([[round(x, 5), round(y, 5)] for x, y in ln.coords])
        a = r['attrs']
        csv_name = SERVICE_MAP[(a.get('trail_name') or '').strip()]
        row = by_name[csv_name]
        props = {'name': csv_name, 'kind': 'atv-bc',
                 'service_name': (a.get('trail_name') or '').strip(),
                 'pub_miles': row['miles'],
                 'manager': row['manager'],
                 'county': row['county(ies)'],
                 'source': row['source_url']}
        if a.get('segment_name'):
            props['segment'] = a['segment_name']
        props['classes'] = ' '.join(x for x in [
            'ATV-I' if a.get('atv_class_1') == 'X' else '',
            'ATV-II' if a.get('atv_class_2') == 'X' else '',
            'OHM' if a.get('off_highway_motorcycle') == 'X' else '',
            'ORV' if a.get('off_road_vehicle') == 'X' else ''] if x)
        if a.get('funding_type'):
            props['funding'] = a['funding_type']
        if a.get('surface_type'):
            props['surface'] = a['surface_type']
        if a.get('web_site'):
            props['website'] = a['web_site']
        out.append({'type': 'Feature', 'properties': props,
                    'geometry': {'type': 'MultiLineString' if len(coords) > 1 else 'LineString',
                                 'coordinates': coords if len(coords) > 1 else coords[0]}})
    gj = {'type': 'FeatureCollection', 'features': out}
    with open(os.path.join(DATA, 'motorized-atv-bc.geojson'), 'w') as f:
        json.dump(gj, f, separators=(',', ':'))
    print('wrote motorized-atv-bc.geojson (%d features, %d bytes)'
          % (len(out), os.path.getsize(os.path.join(DATA, 'motorized-atv-bc.geojson'))))

    drawn_csv = set(gis_mi.keys())
    print('CSV systems drawn on the BC layer: %d' % len(drawn_csv))
    missing = [n for n in SERVICE_MAP.values() if n not in drawn_csv]
    print('SERVICE_MAP systems with no geometry fetched: %s' % (missing or 'none'))

    # ---- panel tables ----
    def on_map(name):
        if name in drawn_csv:
            return 'Drawn — Brainerd–Canada'
        if name in ALREADY_DRAWN_CSV:
            s = 'Drawn (Arrowhead)'
            if name in CLIPPED_ONLY:
                s += ' — 2-mi clip only'
            return s
        return 'List only'

    def table_html(title, names, note=''):
        h = '<h3>%s</h3>' % title
        if note:
            h += '<p>%s</p>' % note
        h += ('<table class="motortable"><thead><tr><th>System</th><th>Miles</th>'
              '<th>Manager</th><th>On map</th></tr></thead><tbody>')
        for name in names:
            row = by_name[name]
            mi = (row['miles'] or '').strip() or '&mdash;'
            mgr = esc(row['manager'])
            om = on_map(name)
            flag = FLAGS.get(name, '')
            if name in LIST_ONLY_REASON and om == 'List only':
                flag = (flag + ' ' if flag else '') + LIST_ONLY_REASON[name]
            disp = esc(name)
            if flag:
                disp += ' <span class="flag">%s</span>' % esc(flag)
            h += ('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                  % (disp, mi, mgr, om))
        h += '</tbody></table>'
        return h

    total_gis = round(sum(gis_mi.values()), 1)
    section = []
    section.append('<h2>Planning &mdash; ATV trails, Brainerd to Canada</h2>')
    section.append('<p><strong>1,630.5 miles of designated ATV trail</strong> from Brainerd to Canada '
                   '(Crow Wing 186.5, Cass 166, Aitkin 89.5, Itasca 420.5, Blue Ox 74, Voyageur Country 36, '
                   'St. Louis 465, Lake 114, Cook 79), against <strong>1.44 miles of off-road foot tread</strong> '
                   'in the Arrowhead gap. ATV-only the total is <strong>1,599.5 miles</strong> — the 1,630.5 '
                   'counts the DNR A-Z rows as published, including three that are not ATV: Miller Hills 14 '
                   '(OHM-only), Alger Grade 13 (OHM-only) and Mesabi Mountain 4 (ORV-only).</p>')
    section.append('<p><strong>Read the total the way the research states it:</strong> 1,630.5 is an arithmetic '
                   'sum of published system mileages, not a surveyed network length. Systems share tread in '
                   'places (the Prospector Loop ties into the Lake and Cook systems; Taconite ATV segments are '
                   'also snowmobile trail; the Blue Ox is also a snowmobile trail in winter), so the total '
                   'contains some double-counted tread. GIS-measured off the DNR service, the systems drawn on '
                   'this layer total <strong>%s mi</strong> — the two figures differ because of segmentation '
                   'and shared tread, and neither is silently substituted for the other.</p>' % format(total_gis, ',.1f'))
    section.append('<p><strong>Where the service geometry diverges most from the published figure:</strong> the DNR service measures Voyageur Country at 116.5 mi against 36 designated miles — the service appears to include signed connector routes beyond the designated trail. Stony Spur II measures 58.9 mi against 30 published — the DNR GeoPDF labels the Stony Spur II + Jackpot loop as 60 miles, so the service geometry is likely the combined loop. Emily-Outing measures 28.3 mi against 56 published, Crow Wing Southern Loop 43.6 against 60, Pine Center 13.5 against 23 — the service appears to carry part of those systems. Rabey Line + Hill City measures 35.1 against 19 published, Moose River Connector 16.7 against 7, Blue Ox 88.1 against 74, Soo Line North (Aitkin) 60.2 against 48. The published figure is used in the tables and popups throughout; the measured figures are shown here so the difference is visible, not hidden.</p>')
    section.append('<p><strong>The corrected Arrowhead core is 1,059.5 miles</strong> (St. Louis 465, Itasca 401.5, '
                   'Lake 114, Cook 79), not the ~1,083 the prior file carried: the prior file double-counted the '
                   'Iron Range OHV State Recreation Area, carrying both a &ldquo;main unit 36&rdquo; row and a '
                   '&ldquo;West Unit 36&rdquo; row. The DNR A-Z lists West Unit 36 and East Unit 13. The wider '
                   '1,630.5 = corrected core 1,059.5 + Crow Wing 186.5 + Cass 166 + Aitkin 89.5 + Blue Ox 74 + '
                   'Voyageur Country 36 + Rabey Line 19.</p>')
    section.append('<p><strong>What the map shows:</strong> this layer (purple, same color as the Arrowhead ATV '
                   'layer) draws the designated systems of the wider corridor <em>whole</em> — Brainerd to the '
                   'Canadian border — from the Minnesota DNR&rsquo;s own OHV trail service. Systems already drawn '
                   'on the Arrowhead layer are not drawn twice; the table marks them &ldquo;Drawn '
                   '(Arrowhead)&rdquo;. Turn the layer on to see the full corridor; the default view is the two '
                   'gaps, so the map zooms to the layer the first time it loads.</p>')
    section.append('<p><strong>Three numbers that must not be added together:</strong> designated miles (the '
                   '1,630.5 above); <em>club-system</em> miles — what a club actually maintains and signs, '
                   'including forest roads and county-road rights-of-way (Voyageur Country is ~200–250 miles of '
                   'signed corridor routes against 36 designated miles; the Northwoods Regional ATV Trail '
                   'Alliance claims 500+ miles, which overlaps the Soo Line corridor figures in the table '
                   'below); and <em>everything legally rideable</em> — the DNR&rsquo;s January 2025 reply to the '
                   'Minnesota Chapter of The Wildlife Society totalled 101,417 miles statewide, including '
                   'unsigned forest-access routes. That last figure is a different universe from designated '
                   'trail and is not used here.</p>')
    section.append('<p><strong>The north end:</strong> the Blue Ox Trail (74 mi, Northome to Littlefork) is the '
                   'only designated ATV trail that physically connects the Itasca systems to the Koochiching / '
                   'Voyageur Country systems. Everything north of it toward Canada is proposed, not built: '
                   'Voyageur Country Phase 2 (up to 125 mi total — 39 existing route + 78 existing with '
                   'improvements + 8 new trail; DNR record of decision April 11, 2025, negative, no EIS ordered; '
                   'permitting stage) and the Blue Ox Connection (about 4.6 mi, Ericsburg to the Blue Ox; LCCMR '
                   '2027 proposal, not funded). The closest designated access toward Canada today is Sheep Ranch '
                   'Road, about 40 miles south of International Falls.</p>')
    section.append('<p><strong>The organizations:</strong> ATV Minnesota (ATVAM), 73 member clubs, est. 1983, '
                   'funded through the ATV Dedicated Account; the Northeastern Regional ATV Joint Powers Board '
                   '(St. Louis, Koochiching and Lake Counties, organized August 2021) coordinates the northeastern '
                   'systems and is currently working to extend the trail from Kabetogama toward Ray and on to '
                   'International Falls and connect it to the Blue Ox. A University of Minnesota Extension study '
                   '(August 2024) estimated 219,230 riders used ATV trails in Koochiching, Lake and St. Louis '
                   'Counties in 2023, contributing $36.1 million in economic activity. ATVAM supports SF 593 / '
                   'SF 594 (2025, funding from the ATV Dedicated Account) and opposes HF 1012 / SF 1245, which '
                   'would end the north/south split in the Highway 2 rule; neither is enacted.</p>')
    section.append('<details><summary>Full system list &mdash; Brainerd to Canada (from the research inventory)</summary>')
    for title, names in TABLES:
        section.append(table_html(title, names))
    section.append(table_html('Proposed — not trails yet', PROPOSED,
                              'Not in any total above.'))
    section.append(table_html('Adjacent systems — context only, NOT in the 1,630.5 total', ADJACENT,
                              'Beltrami, Hubbard, Lake of the Woods and Roseau systems, plus the Carlton County '
                              'end of the Soo Line. Listed for context; not drawn.'))
    section.append('<p class="drawn-note">&ldquo;Drawn — Brainerd–Canada&rdquo; means the system&rsquo;s geometry '
                   'comes from the DNR OHV Trails service (2026 season) and is drawn whole on this layer. '
                   '&ldquo;Drawn (Arrowhead)&rdquo; means it is already on the Arrowhead ATV layer (clipped to '
                   '2 miles around the proposed line / 2004 corridor). &ldquo;List only&rdquo; means no reliable '
                   'geometry was sourced for that system in this pass — it is listed with its published mileage, '
                   'never drawn from an invented line. Published mileages are from the DNR A-Z listing '
                   '(Nov 13, 2026) and county GIA lists; GIS-measured lengths differ. Sources: '
                   'docs/gap-atv-brainerd-canada-research.md and '
                   'docs/gap-atv-brainerd-canada-inventory.csv, Nov 13, 2026.</p>')
    section.append('</details>')
    section_html = '\n'.join(section)

    # ---- inject into index.html ----
    idx_path = os.path.join(BASE, 'index.html')
    with open(idx_path) as f:
        html = f.read()
    start = '<!-- BRAINERD-CANADA-SECTION-START -->'
    end = '<!-- BRAINERD-CANADA-SECTION-END -->'
    if start not in html or end not in html:
        print('ERROR: Brainerd-Canada section markers not in index.html — add them by hand first')
        sys.exit(2)
    html = (html[:html.index(start) + len(start)] + '\n' + section_html + '\n      ' +
            html[html.index(end):])
    with open(idx_path, 'w') as f:
        f.write(html)
    print('injected Brainerd-Canada section into index.html')

    # ---- stats file ----
    stats = {
        'generated': '2026-11-13',
        'sources': {
            'ohv': OHV_FS,
            'inventory': 'docs/gap-atv-brainerd-canada-inventory.csv',
            'research': 'docs/gap-atv-brainerd-canada-research.md',
        },
        'envelope': ENV,
        'ohv_envelope_features': len(ids),
        'bc_features_with_geometry': len(recs),
        'bc_drawn_features': len(out),
        'bc_systems_drawn': sorted(drawn_csv),
        'gis_mi_by_system': {k: round(v, 1) for k, v in sorted(gis_mi.items())},
        'gis_mi_total': total_gis,
        'already_drawn_csv': sorted(ALREADY_DRAWN_CSV),
        'list_only': {n: LIST_ONLY_REASON[n] for n in LIST_ONLY_REASON},
    }
    with open(os.path.join(SRC, 'motorized-bc-stats.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    print('wrote motorized-bc-stats.json')


if __name__ == '__main__':
    main()

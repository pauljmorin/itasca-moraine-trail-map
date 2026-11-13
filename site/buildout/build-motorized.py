#!/usr/bin/env python3
"""Build the motorized-competition layers for the Finishing the Trail
build-out viewer (planning mode, Arrowhead reroute).

Sources (all live, Nov 13, 2026):
- Minnesota DNR OHV Trails, 2026 season — ArcGIS REST FeatureServer
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0
  (the DNR OHV map-service address the ATV research file was missing).
- Minnesota Snowmobile Trails — same host:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0
  (DNR's own snowmobile KMZ, mndnr_snowmobile_trails.kmz, carries the same
  systems; the FeatureServer is used here so both layers come from one
  mechanism with attributes. No contact fields are pulled — public_poc /
  public_pho / pocemail are deliberately excluded.)
- Inventory / published mileages / honest lines: docs/gap-atv-trails-inventory.csv
  and docs/gap-atv-competition-research.md.

Outputs:
- site/buildout/data/motorized-atv.geojson — OHV lines clipped to a 2-mile
  buffer around the proposed Arrowhead line + 2004 corridor + current gap
  line, simplified ~30 m.
- site/buildout/data/motorized-snow.geojson — same for snowmobile lines.
- site/buildout/src/motorized-stats.json — counts, GIS-measured miles,
  overlap metrics, per-system rollup, drawn flags.
- Injects the motorized planning section (headlines + honest lines + system
  list) into site/buildout/index.html between MOTORIZED-SECTION markers.

Overlap method (all in UTM 15N, EPSG:26915):
- inside_corridor_mi: motorized miles whose geometry falls inside the 2004
  corridor polygon.
- near_proposed_mi: proposed-line miles within 100 m of a motorized line
  (i.e. the reroute runs on or beside motorized tread).
- crossings: point intersections between the proposed line and motorized
  lines; shared_mi: length where the proposed line and a motorized line
  coincide (within 100 m).
- near_current_mi: current (official NCTA) gap-line miles within 100 m of a
  motorized line — the road/trail the hiker walks today.
GIS miles are measured off the DNR services and will differ from published
system totals (segmentation, shared tread counted twice). Both are shown;
neither is silently substituted for the other.

Writes build log lines to stdout; exits non-zero on any failure.
"""
import csv, json, math, os, re, sys, urllib.request, urllib.parse

from shapely.geometry import shape, mapping, LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union
from pyproj import Transformer

BASE = os.path.dirname(os.path.abspath(__file__))  # site/buildout
DATA = os.path.join(BASE, 'data')
SRC = os.path.join(BASE, 'src')
REPO = os.path.dirname(os.path.dirname(BASE))  # repo root
UA = {'User-Agent': 'Mozilla/5.0 (build-out viewer data pull)'}

OHV_FS = ('https://enterprise.gisdata.mn.gov/aghost/rest/services/'
          'us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0')
SNOW_FS = ('https://enterprise.gisdata.mn.gov/aghost/rest/services/'
           'us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0')
# Arrowhead planning envelope: Grand Rapids to the Gunflint approach.
ENV = {'xmin': -93.8, 'ymin': 47.3, 'xmax': -91.2, 'ymax': 48.05,
       'spatialReference': {'wkid': 4326}}
BUFFER_M = 3218.69  # 2 miles
NEAR_M = 100.0

TO4326 = Transformer.from_crs('EPSG:26915', 'EPSG:4326', always_xy=True)
TOUTM = Transformer.from_crs('EPSG:4326', 'EPSG:26915', always_xy=True)
MI = 1609.34


def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8'))


def query_fs(base, fields):
    """All features intersecting ENV.
    Two passes: id list first, then fetch by objectIds in chunks. (A single
    envelope geometry query silently dropped 23 features on 2026-11-13 —
    Red Dot segments just south of the envelope and two Voyageur segments
    just north of it — while the id list returned all 1,642. Fetching by id
    closes that gap; the missing features are outside the corridor anyway.)
    """
    params = {
        'where': '1=1',
        'geometry': json.dumps(ENV),
        'geometryType': 'esriGeometryEnvelope',
        'spatialRel': 'esriSpatialRelIntersects',
        'returnIdsOnly': 'true',
        'f': 'json',
    }
    url = base + '/query?' + urllib.parse.urlencode(params)
    ids = fetch_json(url).get('objectIds', [])
    out = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {
            'objectIds': ','.join(str(x) for x in chunk),
            'outFields': ','.join(fields),
            'outSR': '4326',
            'returnGeometry': 'true',
            'f': 'json',
        }
        url = base + '/query?' + urllib.parse.urlencode(params)
        d = fetch_json(url)
        out.extend(d.get('features', []))
    return out


def arcgis_geom_to_shapely(g):
    """ArcGIS JSON polyline -> shapely (Multi)LineString in lon/lat."""
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
    if geom.geom_type == 'Polygon':
        return Polygon([tr.transform(x, y) for x, y in geom.exterior.coords],
                       [[tr.transform(x, y) for x, y in ring.coords]
                        for ring in geom.interiors])
    if geom.geom_type == 'MultiPolygon':
        return MultiPolygon([project(g, tr) for g in geom.geoms])
    raise ValueError('unsupported ' + geom.geom_type)


def load_local_lines(path):
    with open(path) as f:
        gj = json.load(f)
    lines = []
    for feat in gj['features']:
        g = shape(feat['geometry'])
        if g.geom_type == 'LineString':
            lines.append(g)
        elif g.geom_type == 'MultiLineString':
            lines.extend(list(g.geoms))
    return lines


def norm_name(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return ' '.join(s.split())


def main():
    # ---- reference geometries (UTM) ----
    prop_lines = [project(ln, TOUTM) for ln in load_local_lines(os.path.join(DATA, 'proposed-arrowhead.geojson'))]
    gap_lines = [project(ln, TOUTM) for ln in load_local_lines(os.path.join(DATA, 'gap-arrowhead.geojson'))]
    with open(os.path.join(DATA, 'corridor-2004.geojson')) as f:
        corridor4326 = shape(json.load(f)['features'][0]['geometry'])
    corridor = project(corridor4326, TOUTM)
    prop = unary_union(prop_lines)
    gap = unary_union(gap_lines)
    clip_buf = unary_union([prop, corridor, gap]).buffer(BUFFER_M)
    print('clip buffer: 2 mi around proposed line + 2004 corridor + current gap line')

    # ---- pull both services ----
    ohv_fields = ['objectid', 'trail_name', 'segment_name', 'surface_type',
                  'funding_type', 'trail_width', 'atv_class_1', 'atv_class_2',
                  'off_highway_motorcycle', 'off_road_vehicle', 'road_class',
                  'miles', 'web_site', 'program_project']
    snow_fields = ['objectid', 'trail_num', 'miles', 'owner_type', 'trail_name',
                   'maint_by', 'segment_name', 'stud_restr']
    ohv_raw = query_fs(OHV_FS, ohv_fields)
    snow_raw = query_fs(SNOW_FS, snow_fields)
    print('OHV features in envelope: %d' % len(ohv_raw))
    print('snowmobile features in envelope: %d' % len(snow_raw))

    def to_records(raw, kind):
        recs = []
        skipped = 0
        for f in raw:
            g = arcgis_geom_to_shapely(f.get('geometry') or {})
            if g is None or g.is_empty:
                skipped += 1
                continue
            recs.append({'attrs': f.get('attributes') or {}, 'geom4326': g})
        print('%s: %d usable, %d skipped (no geometry)' % (kind, len(recs), skipped))
        return recs

    ohv = to_records(ohv_raw, 'OHV')
    snow = to_records(snow_raw, 'snowmobile')

    # ---- per-system rollup (GIS-measured, UTM) ----
    def rollup(recs):
        by_name = {}
        for r in recs:
            name = (r['attrs'].get('trail_name') or 'Unnamed').strip()
            g = project(r['geom4326'], TOUTM)
            by_name.setdefault(name, {'gis_mi': 0.0, 'features': 0})
            by_name[name]['gis_mi'] += g.length / MI
            by_name[name]['features'] += 1
        return by_name

    ohv_roll = rollup(ohv)
    snow_roll = rollup(snow)
    print('OHV systems in envelope: %d' % len(ohv_roll))
    for n, v in sorted(ohv_roll.items(), key=lambda kv: -kv[1]['gis_mi'])[:12]:
        print('  OHV %-45s %7.1f mi (%d feats)' % (n[:45], v['gis_mi'], v['features']))
    print('snowmobile systems in envelope: %d' % len(snow_roll))
    for n, v in sorted(snow_roll.items(), key=lambda kv: -kv[1]['gis_mi']):
        print('  SNOW %-45s %7.1f mi (%d feats)' % (n[:45], v['gis_mi'], v['features']))

    # ---- overlap metrics (full envelope query, UTM) ----
    def total_length(recs):
        return sum(project(r['geom4326'], TOUTM).length for r in recs) / MI

    def inside_corridor(recs):
        tot = 0.0
        for r in recs:
            g = project(r['geom4326'], TOUTM)
            inter = g.intersection(corridor)
            if not inter.is_empty:
                tot += inter.length / MI
        return tot

    def near_line(recs, line, dist=NEAR_M):
        buf = line.buffer(dist)
        tot = 0.0
        for r in recs:
            g = project(r['geom4326'], TOUTM)
            inter = g.intersection(buf)
            if not inter.is_empty:
                tot += inter.length / MI
        return tot

    def crossings(recs, line):
        """Crossing LOCATIONS between the proposed line and motorized lines.
        Raw point intersections are misleading: where the proposed line runs
        along a motorized corridor the two digitizations weave across each
        other dozens of times (the Taconite–Big Aspen Connection alone gave
        227 raw points). Points within 250 m of each other count as one
        location. Returns (locations, shared_mi, per-system raw points).
        """
        pts = []
        per_system = {}
        for r in recs:
            g = project(r['geom4326'], TOUTM)
            inter = g.intersection(line)
            if inter.is_empty:
                continue
            name = (r['attrs'].get('trail_name') or 'Unnamed').strip()
            got = []
            if inter.geom_type == 'Point':
                got = [inter]
            elif inter.geom_type == 'MultiPoint':
                got = list(inter.geoms)
            elif inter.geom_type == 'GeometryCollection':
                for gg in inter.geoms:
                    if gg.geom_type == 'Point':
                        got.append(gg)
                    elif gg.geom_type == 'MultiPoint':
                        got.extend(gg.geoms)
            pts.extend(got)
            per_system[name] = per_system.get(name, 0) + len(got)
        locations = 0
        if pts:
            clusters = unary_union([p.buffer(250) for p in pts])
            locations = len(clusters.geoms) if clusters.geom_type == 'MultiPolygon' else 1
        return locations, per_system

    def near_proposed_by_system(recs, line, dist=NEAR_M):
        """Proposed-line miles within `dist` of each system — the honest
        version of 'the reroute follows this corridor'."""
        by_name = {}
        for r in recs:
            name = (r['attrs'].get('trail_name') or 'Unnamed').strip()
            by_name.setdefault(name, []).append(project(r['geom4326'], TOUTM))
        out = {}
        for name, geoms in by_name.items():
            buf = unary_union(geoms).buffer(dist)
            inter = line.intersection(buf)
            if not inter.is_empty:
                out[name] = inter.length / MI
        return out

    metrics = {}
    for kind, recs in (('atv', ohv), ('snow', snow)):
        m = {
            'envelope_mi': round(total_length(recs), 1),
            'inside_corridor_mi': round(inside_corridor(recs), 1),
            'near_proposed_mi': round(near_line(recs, prop), 1),
            'near_current_mi': round(near_line(recs, gap), 1),
        }
        locs, per_system = crossings(recs, prop)
        m['proposed_crossing_locations'] = locs
        m['proposed_crossing_raw_points'] = sum(per_system.values())
        m['near_proposed_by_system_mi'] = {k: round(v, 1) for k, v in
            sorted(near_proposed_by_system(recs, prop).items(), key=lambda kv: -kv[1])[:6]}
        metrics[kind] = m
        print('%s: envelope %.1f mi; inside 2004 corridor %.1f mi; within 100 m of proposed line %.1f mi; '
              'crossing locations with proposed line %d (raw points %d); within 100 m of current line %.1f mi'
              % (kind, m['envelope_mi'], m['inside_corridor_mi'], m['near_proposed_mi'],
                 locs, m['proposed_crossing_raw_points'], m['near_current_mi']))
        print('   raw crossing points by system:', dict(sorted(per_system.items(), key=lambda kv: -kv[1])[:6]))
        print('   proposed-line miles within 100 m, by system:', m['near_proposed_by_system_mi'])

    # ---- clip + simplify for the viewer ----
    def build_geojson(recs, kind):
        out = []
        n_clipped = 0
        for r in recs:
            g = project(r['geom4326'], TOUTM)
            c = g.intersection(clip_buf)
            if c.is_empty:
                continue
            c = c.simplify(30)  # ~30 m
            if c.is_empty:
                continue
            n_clipped += 1
            c4326 = project(c, TO4326)
            geoms = list(c4326.geoms) if c4326.geom_type == 'MultiLineString' else [c4326]
            coords = []
            for ln in geoms:
                coords.append([[round(x, 5), round(y, 5)] for x, y in ln.coords])
            a = r['attrs']
            props = {'name': (a.get('trail_name') or 'Unnamed').strip(),
                     'kind': kind}
            if a.get('segment_name'):
                props['segment'] = a['segment_name']
            if kind == 'atv':
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
                if a.get('miles') is not None:
                    props['pub_miles'] = a['miles']
            else:
                if a.get('maint_by'):
                    props['maintained_by'] = a['maint_by']
                if a.get('owner_type'):
                    props['owner'] = a['owner_type']
                if a.get('trail_num') is not None:
                    props['trail_num'] = a['trail_num']
                if a.get('stud_restr'):
                    props['stud_restr'] = a['stud_restr']
                if a.get('miles') is not None:
                    props['pub_miles'] = a['miles']
            out.append({'type': 'Feature', 'properties': props,
                        'geometry': {'type': 'MultiLineString' if len(coords) > 1 else 'LineString',
                                     'coordinates': coords if len(coords) > 1 else coords[0]}})
        print('%s: %d features drawn (clipped to 2-mi buffer)' % (kind, n_clipped))
        return {'type': 'FeatureCollection', 'features': out}

    atv_gj = build_geojson(ohv, 'atv')
    snow_gj = build_geojson(snow, 'snow')
    with open(os.path.join(DATA, 'motorized-atv.geojson'), 'w') as f:
        json.dump(atv_gj, f, separators=(',', ':'))
    with open(os.path.join(DATA, 'motorized-snow.geojson'), 'w') as f:
        json.dump(snow_gj, f, separators=(',', ':'))
    print('wrote motorized-atv.geojson (%d bytes)' %
          os.path.getsize(os.path.join(DATA, 'motorized-atv.geojson')))
    print('wrote motorized-snow.geojson (%d bytes)' %
          os.path.getsize(os.path.join(DATA, 'motorized-snow.geojson')))

    # ---- drawn flags: which CSV systems appear in the drawn files ----
    drawn_names = set()
    for gj in (atv_gj, snow_gj):
        for feat in gj['features']:
            drawn_names.add(norm_name(feat['properties']['name']))

    # CSV names and DNR service names differ in wording ("ATV" inserted
    # mid-name, "Bigfork" vs "Big Fork", Gilbert main unit = East Unit in
    # the service). Substring matching alone misses those — explicit aliases.
    ALIASES = {
        'quad cities atv trail': 'quad cities trail',
        'iron range ohv state recreation area gilbert main unit':
            'iron range ohv state recreation area east unit',
        'alborn pengilly railroad trail':
            'alborn pengilly railroad state trail ms84 029',
        'bigfork and balsam connection': 'big fork and balsam b b connection trail',
        'len hardy trail': 'len hardy memorial trail',
        'east range multi use trail': 'east range multi use ohv trail',
        'taconite state trail big aspen connection':
            'taconite big aspen connection',
    }

    def drawn_for(csv_name):
        n = norm_name(csv_name)
        if n in drawn_names:
            return True
        if ALIASES.get(n) in drawn_names:
            return True
        # the FS names are sometimes shorter/longer than the CSV names;
        # accept a strong prefix/substring match either way
        for d in drawn_names:
            if (len(n) > 8 and len(d) > 8) and (n in d or d in n):
                return True
        return False

    # ---- system list from the CSV ----
    csv_path = os.path.join(REPO, 'docs', 'gap-atv-trails-inventory.csv')
    rows = []
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            rows.append(row)
    print('CSV rows: %d' % len(rows))

    # short flags for the rows the research file marks as disputed/derived
    FLAGS = {
        'prospectors trail prospector loop': 'Mileage disputed: DNR 167 mi; club 216+ mi; consultant 250 mi.',
        'voyageur country atv trail': 'County disputed: DNR A-Z says Lake; EAW and club place it in Koochiching / St. Louis. Phase 2 proposes +125 mi roadway + 76 mi natural-surface trail (EAW stage, not built).',
        'superior nf big aspen trail system': 'Excluded from the corridor total — overlap with the 18-mi Taconite–Big Aspen Connection unresolved.',
        'taconite state trail big aspen connection': 'Overlap with the 21-mi USFS Big Aspen system unresolved — do not add both.',
        'tomahawk trail': 'Included in the Ely Igloo 152-mi system total — do not add.',
        'ely igloo other gia trails': 'Arithmetic: 152-mi club total minus 82-mi Tomahawk — not a published figure.',
        'david dill arrowhead state trail': 'Mileage disputed: 135 mi (DNR trail pages) vs 126 mi (DNR map PDFs).',
        'stony spur ii trail': 'Riderplanet lists 26 mi; DNR figure used.',
        'c j ramstad north shore state trail atv segment': 'HF 274 (2025) proposes ATV use on Cook and Lake County portions.',
        'ely igloo snowmobile club system all gia trails': 'Groomed system around Ely; includes the Tomahawk Trail (82 mi), which is drawn on the map — do not add rows together.',
    }
    COUNTY_TOTAL = 'County total — overlaps the named systems above; NOT additive.'
    BLANK = 'Mileage not found in sources retrieved — left blank, not estimated.'

    def flag_for(row):
        n = norm_name(row['name'])
        if n in FLAGS:
            return FLAGS[n]
        if 'county total' in row['corridor_overlap_notes'].lower() and 'not additive' in row['corridor_overlap_notes'].lower():
            return COUNTY_TOTAL
        if not (row['miles'] or '').strip():
            return BLANK
        return ''

    def section_rows(pred):
        return [r for r in rows if pred(r)]

    atv_core = [r for r in rows if r['vehicle'] == 'ATV' and 'ADJACENT' not in r['corridor_overlap_notes']]
    atv_adj = [r for r in rows if r['vehicle'] == 'ATV' and 'ADJACENT' in r['corridor_overlap_notes']]
    atv_prop = [r for r in rows if r['vehicle'] == 'ATV' and r['status'] not in ('built', 'built/under construction')]
    snow_named = [r for r in rows if r['vehicle'] == 'snowmobile' and 'COUNTY TOTAL' not in r['corridor_overlap_notes']]
    snow_county = [r for r in rows if r['vehicle'] == 'snowmobile' and 'COUNTY TOTAL' in r['corridor_overlap_notes']]
    shared_rows = [r for r in rows if r['vehicle'] == 'shared']

    def table_html(title, rs, note=''):
        if not rs:
            return ''
        h = '<h3>%s</h3>' % title
        if note:
            h += '<p>%s</p>' % note
        h += ('<table class="motortable"><thead><tr><th>System</th><th>Miles</th>'
              '<th>Status</th><th>On map</th></tr></thead><tbody>')
        for r in rs:
            mi = (r['miles'] or '').strip() or '&mdash;'
            st = r['status']
            dr = 'Drawn' if drawn_for(r['name']) else 'List only'
            flag = flag_for(r)
            name = r['name']
            if flag:
                name += ' <span class="flag">%s</span>' % flag
            h += ('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                  % (name, mi, st, dr))
        h += '</tbody></table>'
        return h

    atv_m = metrics['atv']
    sn_m = metrics['snow']
    section = []
    section.append('<h2>Planning &mdash; motorized competition (ATV &amp; snowmobile)</h2>')
    section.append('<p><strong>About 1,083 miles of designated ATV trail</strong> in the four corridor counties '
                   '(St. Louis 488, Itasca 401.5, Lake 114, Cook 79 &mdash; sums of published system mileages, '
                   'not a surveyed network length), against <strong>1.44 miles of off-road foot tread</strong> '
                   'in the Arrowhead gap. The ATV network is the dominant recreational trail system in the '
                   'corridor by mileage, it is still expanding, and it is backed by a dedicated funding '
                   'account the NCT does not have.</p>')
    section.append('<p><strong>What the map shows:</strong> ATV lines (purple) and snowmobile lines (blue) '
                   'within 2 miles of the proposed Arrowhead line and the 2004 corridor, from the Minnesota '
                   'DNR&rsquo;s own trail services. GIS-measured in the corridor: '
                   '<strong>%.1f mi of ATV trail inside the 2004 corridor</strong> and '
                   '<strong>%.1f mi of snowmobile trail inside it</strong>. The proposed line runs within '
                   '100 m of motorized trail for <strong>%.1f mi (ATV)</strong> and '
                   '<strong>%.1f mi (snowmobile)</strong>, crossing ATV trail at %d locations and snowmobile '
                   'trail at %d locations. The current official line already runs within 100 m of motorized '
                   'trail for %.1f mi (ATV) and %.1f mi (snowmobile). Mileages are GIS-measured off the DNR '
                   'services, Nov 13, 2026 &mdash; they will differ from published system totals, which are '
                   'shown in the table below. Crossing locations cluster intersection points within 250 m: '
                   'where the proposed line runs along a motorized corridor the two digitizations weave '
                   'across each other, so raw point counts would overstate the crossings.</p>' % (
                       atv_m['inside_corridor_mi'], sn_m['inside_corridor_mi'],
                       atv_m['near_proposed_mi'], sn_m['near_proposed_mi'],
                       atv_m['proposed_crossing_locations'], sn_m['proposed_crossing_locations'],
                       atv_m['near_current_mi'], sn_m['near_current_mi']))
    section.append('<p><strong>The headline overlap:</strong> the proposed line does not avoid the motorized '
                   'system &mdash; it runs alongside it. <strong>50.9 of its 101.4 miles lie within 100 m of '
                   'the Taconite State Trail</strong> (the groomed snowmobile spine, Grand Rapids to Ely), '
                   'and <strong>16.6 miles lie within 100 m of the Taconite&ndash;Big Aspen ATV '
                   'connection</strong>. The reroute would share the Taconite corridor for roughly half its '
                   'length: easier land in one sense, direct competition for the same tread in another.</p>')
    section.append('<p><strong>The Highway 2 rule, stated honestly:</strong> north of U.S. Highway 2, unsigned '
                   'forest access routes in managed state forests are open to OHV riding unless posted closed '
                   '(Minn. Stat. &sect; 84.777) &mdash; and user-created routes get used with little consequence. '
                   'That is a rule about <em>riding</em> unsigned routes, not a right to <em>build</em> a trail: '
                   'building a new trail needs DNR designation and posting, and environmental review. '
                   'HF 1012 / SF 1245 would end the north/south split (signed trails only statewide); '
                   'neither is enacted. Most county roads in St. Louis County are also open to ATVs, so the '
                   'road walk hikers use today is largely rideable already.</p>')
    section.append('<p><strong>Snowmobiles are a different competition:</strong> they do not rut tread the way '
                   'wheeled vehicles do, but they need wide groomed corridors &mdash; 20&ndash;26 ft for a shared '
                   'segment, 32&ndash;36 ft at crossings &mdash; and groomers up to 17,000 lb. The 165-mile Taconite '
                   'State Trail runs Grand Rapids to Ely, the same endpoints as the gap, as a groomed '
                   'snowmobile spine. Named snowmobile systems total 598 miles.</p>')
    section.append('<p><strong>The organizations:</strong> ATV Minnesota, 73 member clubs (est. 1983), funded '
                   'through the ATV Dedicated Account ($60 per three-year registration plus unrefunded gas tax); '
                   'MnUSA, 250+ clubs and 10,000+ members, funded through the snowmobile trails and enforcement '
                   'account. IRRR granted $2.16 million to five ATV clubs in a single board meeting (May 2025), '
                   'and LCCMR funded the Moose and Seven Beaver ATV upgrade &mdash; the same fund the NCT planning '
                   'proposal targets.</p>')
    section.append('<p class="drawn-note">The deconfliction-meeting claim &mdash; that the NCT is not at the table '
                   'while Mesabi, ATV, ski and snowmobile interests are &mdash; is reported in the chapter&rsquo;s '
                   'folder but was not verified against any meeting record; it is not asserted here as fact.</p>')
    section.append('<details><summary>Full system list &mdash; ATV and snowmobile (from the research inventory)</summary>')
    section.append(table_html('ATV systems &mdash; corridor core (St. Louis, Itasca, Lake, Cook)', atv_core,
                              'Sums of published system mileages. Systems share tread in places, so the ~1,083-mi '
                              'total is an order-of-magnitude statement, not a precise network length.'))
    section.append(table_html('ATV systems &mdash; adjacent (not in the corridor total)', atv_adj))
    section.append(table_html('Shared-use segments (ATV on a snowmobile / state-trail spine)', shared_rows))
    section.append(table_html('Snowmobile named systems', snow_named,
                              'Named-system total 598 miles (165 + 135 + 146 + 152). System totals, not '
                              'corridor-clipped.'))
    section.append(table_html('Snowmobile county totals (context only &mdash; NOT additive)', snow_county))
    section.append('<p class="drawn-note">&ldquo;Drawn&rdquo; means the system&rsquo;s geometry from the DNR '
                   'service falls within 2 miles of the proposed line or the 2004 corridor and is drawn on the '
                   'map. &ldquo;List only&rdquo; means no reliable geometry was sourced for that system in this '
                   'pass (proposed, out of the drawn area, or no GIS found) &mdash; it is listed with its '
                   'published mileage and status, never drawn from an invented line. Sources: '
                   'docs/gap-atv-competition-research.md and docs/gap-atv-trails-inventory.csv, Nov 13, 2026.</p>')
    section.append('</details>')
    section_html = '\n'.join(section)

    # ---- inject into index.html ----
    idx_path = os.path.join(BASE, 'index.html')
    with open(idx_path) as f:
        html = f.read()
    start = '<!-- MOTORIZED-SECTION-START -->'
    end = '<!-- MOTORIZED-SECTION-END -->'
    if start not in html or end not in html:
        print('ERROR: motorized section markers not in index.html — add them by hand first')
        sys.exit(2)
    html = (html[:html.index(start) + len(start)] + '\n' + section_html + '\n      ' +
            html[html.index(end):])
    with open(idx_path, 'w') as f:
        f.write(html)
    print('injected motorized section into index.html')

    # ---- stats file ----
    stats = {
        'generated': '2026-11-13',
        'sources': {
            'ohv': OHV_FS,
            'snowmobile': SNOW_FS,
            'inventory': 'docs/gap-atv-trails-inventory.csv',
            'research': 'docs/gap-atv-competition-research.md',
        },
        'buffer_mi': 2.0,
        'near_m': NEAR_M,
        'ohv_envelope_features': len(ohv),
        'snow_envelope_features': len(snow),
        'ohv_drawn_features': len(atv_gj['features']),
        'snow_drawn_features': len(snow_gj['features']),
        'metrics': metrics,
        'ohv_systems_gis_mi': {k: round(v['gis_mi'], 1) for k, v in sorted(ohv_roll.items())},
        'snow_systems_gis_mi': {k: round(v['gis_mi'], 1) for k, v in sorted(snow_roll.items())},
        'csv_drawn': {r['name']: drawn_for(r['name']) for r in rows},
    }
    with open(os.path.join(SRC, 'motorized-stats.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    print('wrote motorized-stats.json')


if __name__ == '__main__':
    main()

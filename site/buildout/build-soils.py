#!/usr/bin/env python3
"""Build the soils layer for the Finishing the Trail build-out viewer.

Part A — SSURGO map-unit polygons clipped to a 0.5-mile buffer around the
two gap lines (site/buildout/data/gap-*.geojson), via USDA NRCS Soil Data
Access (SDA) tabular REST: mukeys intersecting the buffer, then mupolygon
WKT + mapunit/muaggatt attributes. Output: site/buildout/data/soils-corridor.geojson.

Part B — NLCD 2021 class histogram inside the same buffer, via MRLC
GeoServer WCS GetCoverage (mrlc_display:NLCD_2021_Land_Cover_L48), masked
to the buffer with PIL. Output: site/buildout/src/nlcd-corridor-stats.json
(used for the viewer legend).

Writes build log lines to stdout; exits non-zero on any failure.
"""
import json, math, os, sys, urllib.request, urllib.parse
from collections import Counter

from shapely.geometry import shape, mapping, LineString, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely import to_wkt, from_wkt
from pyproj import Transformer

BASE = os.path.dirname(os.path.abspath(__file__))  # site/buildout
DATA = os.path.join(BASE, 'data')
SRC = os.path.join(BASE, 'src')
SDA = 'https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
MRLC_WCS = 'https://www.mrlc.gov/geoserver/wcs'
BUFFER_M = 804.67  # 0.5 mile
UA = {'User-Agent': 'Mozilla/5.0 (build-out viewer data pull)'}

TO4326 = Transformer.from_crs('EPSG:26915', 'EPSG:4326', always_xy=True)
TOUTM = Transformer.from_crs('EPSG:4326', 'EPSG:26915', always_xy=True)


def sda(sql):
    data = json.dumps({'query': sql, 'format': 'JSON'}).encode()
    req = urllib.request.Request(SDA, data=data,
                                 headers={'Content-Type': 'application/json', **UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8'))['Table']


def project(geom, tr):
    if geom.geom_type == 'LineString':
        return LineString([tr.transform(x, y) for x, y in geom.coords])
    if geom.geom_type == 'MultiLineString':
        from shapely.geometry import MultiLineString
        return MultiLineString([project(g, tr) for g in geom.geoms])
    if geom.geom_type == 'Polygon':
        return Polygon([tr.transform(x, y) for x, y in geom.exterior.coords],
                       [[tr.transform(x, y) for x, y in ring.coords]
                        for ring in geom.interiors])
    if geom.geom_type == 'MultiPolygon':
        return MultiPolygon([project(g, tr) for g in geom.geoms])
    raise ValueError('unsupported ' + geom.geom_type)


def load_gap_lines(path):
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


def build_buffer(gap_path):
    lines = load_gap_lines(gap_path)
    utm = [project(ln, TOUTM) for ln in lines]
    merged = unary_union(utm)
    buf = merged.buffer(BUFFER_M)
    buf = buf.simplify(100)  # ~100 m, keeps WKT small for SDA
    buf4326 = project(buf, TO4326)
    # round coords to 5 decimals (~1 m)
    return buf4326


def wkt_of(geom):
    return to_wkt(geom, rounding_precision=5)


def polys_from_wkt(wkt):
    g = from_wkt(wkt)
    if g.geom_type == 'Polygon':
        return [g]
    if g.geom_type == 'MultiPolygon':
        return list(g.geoms)
    return []


def main():
    # ---- buffers ----
    buffers = {}
    for gap in ('arrowhead', 'western'):
        buf = build_buffer(os.path.join(DATA, 'gap-%s.geojson' % gap))
        buffers[gap] = buf
        polys = list(buf.geoms) if buf.geom_type == 'MultiPolygon' else [buf]
        print('buffer %s: %d polygon(s), %d vertices total' %
              (gap, len(polys), sum(len(p.exterior.coords) for p in polys)))
        with open(os.path.join(SRC, 'corridor-buffer-%s.geojson' % gap), 'w') as f:
            json.dump({'type': 'Feature', 'properties': {'gap': gap, 'buffer_m': BUFFER_M},
                       'geometry': mapping(buf)}, f)

    # ---- SDA: mukeys + mupolygonkeys intersecting each buffer ----
    mukeys = {}  # mukey -> set of gaps
    polykeys = {}  # mupolygonkey -> set of gaps
    for gap, buf in buffers.items():
        polys = list(buf.geoms) if buf.geom_type == 'MultiPolygon' else [buf]
        for i, poly in enumerate(polys):
            # simplify to ~200 m for the SDA WKT (keeps the request small;
            # the saved buffer file stays at 100 m)
            wkt = wkt_of(poly.simplify(0.002))
            rows = sda("SELECT mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('%s')" % wkt)
            for (mk,) in rows:
                mukeys.setdefault(int(mk), set()).add(gap)
            rows = sda("SELECT mupolygonkey FROM SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('%s')" % wkt)
            for (pk,) in rows:
                polykeys.setdefault(int(pk), set()).add(gap)
            print('  %s poly %d/%d: %d mukeys, %d mupolygonkeys' %
                  (gap, i + 1, len(polys), len(mukeys), len(polykeys)))
        print('mukeys total so far: %d; mupolygonkeys: %d' % (len(mukeys), len(polykeys)))

    mukey_list = sorted(mukeys)
    print('unique mukeys intersecting corridor buffer: %d' % len(mukey_list))
    print('unique mupolygonkeys intersecting corridor buffer: %d' % len(polykeys))

    # ---- SDA: attributes (column names verified live) ----
    attrs = {}
    try:
        rows = sda('SELECT TOP 1 mukey, drclassdcd, slopegradwta, flodfreqdcd FROM muaggatt')
        print('muaggatt cols OK:', rows)
    except Exception as e:
        print('muaggatt column test FAILED:', e)
        sys.exit(2)
    for i in range(0, len(mukey_list), 200):
        chunk = mukey_list[i:i + 200]
        inlist = ','.join(str(m) for m in chunk)
        for (mk, musym, muname) in sda(
                'SELECT mukey, musym, muname FROM mapunit WHERE mukey IN (%s)' % inlist):
            attrs.setdefault(int(mk), {}) \
                .update({'musym': musym, 'muname': muname})
        for row in sda(
                'SELECT mukey, drclassdcd, slopegradwta, flodfreqdcd FROM muaggatt WHERE mukey IN (%s)' % inlist):
            mk = int(row[0])
            attrs.setdefault(mk, {}).update(
                {'drainage': row[1], 'slope': row[2], 'flood': row[3]})
        # hydric flag from the major components (muaggatt has no hydric column)
        hyd = {}
        for (mk, hr) in sda(
                "SELECT mukey, hydricrating FROM component WHERE mukey IN (%s) AND majcompflag = 'Yes'" % inlist):
            mk = int(mk)
            if hr == 'Yes':
                hyd[mk] = 'Yes'
            elif mk not in hyd:
                hyd[mk] = hr
        for mk, hr in hyd.items():
            attrs.setdefault(mk, {})['hydric'] = hr
        print('  attrs chunk %d-%d' % (i, min(i + 200, len(mukey_list))))

    # ---- SDA: polygons, by mupolygonkey (only polygons that touch the buffer) ----
    feats = []
    skipped_no_geom = 0
    pk_list = sorted(polykeys)
    for i in range(0, len(pk_list), 100):
        chunk = pk_list[i:i + 100]
        inlist = ','.join(str(p) for p in chunk)
        rows = sda('SELECT mupolygonkey, mukey, mupolygongeo FROM mupolygon WHERE mupolygonkey IN (%s)' % inlist)
        for (pk, mk, wkt) in rows:
            mk = int(mk)
            try:
                geoms = polys_from_wkt(wkt)
            except Exception:
                skipped_no_geom += 1
                continue
            for g in geoms:
                feats.append((mk, g))
        print('  polygons chunk %d-%d: %d features so far' %
              (i, min(i + 100, len(pk_list)), len(feats)))
    print('raw mupolygon features: %d (skipped bad: %d)' % (len(feats), skipped_no_geom))

    # ---- clip to buffer, simplify, round ----
    union_buf = unary_union(list(buffers.values()))
    out = []
    for mk, g in feats:
        try:
            c = g.intersection(union_buf)
        except Exception:
            continue
        if c.is_empty:
            continue
        c = c.simplify(0.0008)  # ~70-90 m
        if c.is_empty:
            continue
        geoms = list(c.geoms) if c.geom_type == 'MultiPolygon' else [c]
        a = attrs.get(mk, {})
        for pg in geoms:
            coords = [[ [round(x, 4), round(y, 4)] for x, y in ring.coords]
                      for ring in [pg.exterior] + list(pg.interiors)]
            rings = [coords[0]] + coords[1:]
            out.append({'type': 'Feature',
                        'properties': {
                            'mukey': mk,
                            'musym': a.get('musym'),
                            'muname': a.get('muname'),
                            'drainage': a.get('drainage'),
                            'hydric': a.get('hydric'),
                            'slope': a.get('slope'),
                            'flood': a.get('flood'),
                            'gap': ','.join(sorted(mukeys.get(mk, [])))},
                        'geometry': {'type': 'Polygon', 'coordinates': rings}})
    print('clipped+simplified features: %d' % len(out))
    gj = {'type': 'FeatureCollection', 'features': out}
    opath = os.path.join(DATA, 'soils-corridor.geojson')
    with open(opath, 'w') as f:
        json.dump(gj, f, separators=(',', ':'))
    print('wrote %s (%d bytes)' % (opath, os.path.getsize(opath)))

    # ---- NLCD histogram inside the buffer (WCS, per gap bbox) ----
    from PIL import Image, ImageDraw
    import numpy as np
    stats = {}
    for gap, buf in buffers.items():
        minx, miny, maxx, maxy = buf.bounds
        w, h = 1600, int(1600 * (maxy - miny) / (maxx - minx))
        params = {'SERVICE': 'WCS', 'VERSION': '1.0.0', 'REQUEST': 'GetCoverage',
                  'COVERAGE': 'mrlc_display:NLCD_2021_Land_Cover_L48',
                  'CRS': 'EPSG:4326', 'BBOX': '%f,%f,%f,%f' % (minx, miny, maxx, maxy),
                  'WIDTH': str(w), 'HEIGHT': str(h), 'FORMAT': 'GeoTIFF'}
        url = MRLC_WCS + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            tif = r.read()
        print('WCS %s: %d bytes' % (gap, len(tif)))
        tmp = '/tmp/nlcd-%s.tif' % gap
        open(tmp, 'wb').write(tif)
        im = Image.open(tmp)
        arr = np.array(im)
        # mask: rasterize buffer polygons into image coords
        mask = Image.new('1', (w, h), 0)
        dr = ImageDraw.Draw(mask)
        polys = list(buf.geoms) if buf.geom_type == 'MultiPolygon' else [buf]
        for poly in polys:
            for ring in [poly.exterior] + list(poly.interiors):
                px = [((x - minx) / (maxx - minx) * w,
                       (1 - (y - miny) / (maxy - miny)) * h) for x, y in ring.coords]
                dr.polygon(px, fill=1)
        m = np.array(mask).astype(bool)
        vals = arr[m]
        c = Counter(int(v) for v in vals.tolist())
        stats[gap] = {'pixels': int(m.sum()), 'classes': {str(k): v for k, v in sorted(c.items())}}
        print('  %s in-buffer pixels: %d, classes: %s' % (gap, int(m.sum()), dict(c)))
    with open(os.path.join(SRC, 'nlcd-corridor-stats.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    print('wrote nlcd-corridor-stats.json')


if __name__ == '__main__':
    main()

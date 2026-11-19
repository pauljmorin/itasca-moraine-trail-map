#!/usr/bin/env python3
"""Wire the 26 passing points from the Nov 18 41-candidate Street View
check into the main layer (site/data/streetview.geojson, 30 -> 56).

Sources (all on disk, no new browser work):
- docs/streetview-verification-queue-2026-11-18.md : candidate lat/lon + point text
- docs/street-view-41-check-2026-11-18.md : pass/fail, imagery year, heading
  (confirmed or corrected), and the pano notes.

Rules:
- Only PASS points enter. The 15 FAILs stay out (incl. all 7 Priority 2
  Walker-Hackensack crossings: no SV coverage there at all).
- Heading is the check's confirmed/corrected value, not the suggested one
  (#2 229->180, #6 228->120, #8 9->100, #38 345->45).
- Imagery is year-only: the browser check could read only the "(c) YYYY"
  watermark year. "not legible" where the year could not be read.
- why = the queue doc's point description verbatim; pano_note = the
  check's notes verbatim. Nothing invented.
- trail_lat/trail_lon = pano coords (viewpoints sit on the road-walk road).
- Dedupes against existing features by (pano_lat, pano_lon).
"""
import json
import re
import sys

REPO = '/home/hatch/workspace/itasca-trail-map'
QUEUE = f'{REPO}/docs/streetview-verification-queue-2026-11-18.md'
CHECK = f'{REPO}/docs/street-view-41-check-2026-11-18.md'
LAYER = f'{REPO}/site/data/streetview.geojson'

# name / road / faces for each passing point (short, in the existing style)
HAND = {
    1: ("Kawishiwi Ranger Station entrance, Ely", "Fernberg Rd", "the road walk on Fernberg Rd"),
    2: ("Kawishiwi Falls Trailhead", "Fernberg Rd", "the trailhead"),
    3: ("Forest History Rd, Grand Rapids", "Forest History Rd", "the road walk on Forest History Rd"),
    4: ("14th Ave SW, Grand Rapids", "14th Ave SW", "the road walk on 14th Ave SW"),
    5: ("Park trail, Grand Rapids", "SW 12th Ave", "the park trail"),
    6: ("Corey St / US-169, Grand Rapids", "US-169", "the road walk on US-169"),
    7: ("Co Rd 76, Grand Rapids area", "Co Rd 76", "the road walk on Co Rd 76"),
    8: ("Mesabi Trail parking area, Grand Rapids", "Mesabi Trail", "the Mesabi Trail leaving the parking area"),
    9: ("S Second St, Tower", "S Second St", "the road walk on S Second St"),
    10: ("Hwy 22, Kent area", "Hwy 22", "the road walk on Hwy 22"),
    11: ("Broadway bridge over the Red River", "Broadway", "the road walk on Broadway"),
    12: ("Co Hwy 3, Otter Tail Co", "Co Hwy 3", "the road walk on Co Hwy 3"),
    14: ("City Beach Rd, Vergas", "City Beach Rd", "the road walk on City Beach Rd"),
    15: ("CSAH 41 / CSAH 4, Vergas", "CSAH 41", "the road walk on CSAH 41"),
    16: ("E Wymer Lake Rd, Frazee area", "E Wymer Lake Rd", "the road walk on E Wymer Lake Rd"),
    17: ("Hwy 228, Frazee area", "Hwy 228", "the road walk on Hwy 228"),
    20: ("Hubbel Pond trailhead, Hwy 34", "Hwy 34", "the trailhead"),
    21: ("Co Hwy 29, Frazee area", "Co Hwy 29", "the road walk on Co Hwy 29"),
    24: ("3rd Ave SW, Fergus Falls", "3rd Ave SW", "the road walk on 3rd Ave SW"),
    25: ("179th Ave / Co Rd 88, Rothsay area", "Co Rd 88", "the road walk on Co Rd 88"),
    26: ("Co Rd 88, Rothsay area", "Co Rd 88", "the road walk on Co Rd 88"),
    28: ("245th St, Fergus Falls area", "245th St", "the trail crossing the field"),
    30: ("Otter Trail Scenic Byway (Co Rd 3)", "Co Rd 3", "the road walk on Co Rd 3"),
    38: ("Co Rd 4, Vergas area", "Co Rd 4", "the road walk on Co Rd 4"),
    39: ("N River Dr, Frazee", "N River Dr", "the road walk on N River Dr"),
    40: ("Co Hwy 29, Frazee area", "Co Hwy 29", "the road walk on Co Hwy 29"),
}


def parse_queue(path):
    out = {}
    for line in open(path):
        m = re.match(r'\| (\d+) \| (.+?) \| [^|]+ \| \d \| ([\d.\-]+), ([\d.\-]+) \|', line)
        if m:
            out[int(m.group(1))] = {
                'point': m.group(2).strip(),
                'lat': float(m.group(3)),
                'lon': float(m.group(4)),
            }
    return out


def parse_check(path):
    out = {}
    for line in open(path):
        m = re.match(r'\| (\d+) \| (PASS|FAIL) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', line)
        if not m:
            continue
        n = int(m.group(1))
        heading_cell = m.group(4).strip()
        corr = re.search(r'CORRECTED ~(\d+)', heading_cell)
        heading = int(corr.group(1)) if corr else int(re.search(r'(\d+)', heading_cell).group(1))
        img = m.group(3).strip()
        img = img.replace('©', '') if img.startswith('©') else img
        out[n] = {
            'pass': m.group(2) == 'PASS',
            'imagery': img,
            'heading': heading,
            'notes': m.group(5).strip(),
        }
    return out


def main():
    queue = parse_queue(QUEUE)
    check = parse_check(CHECK)
    assert len(queue) == 41, f'queue rows: {len(queue)}'
    assert len(check) == 41, f'check rows: {len(check)}'
    passing = sorted(n for n, c in check.items() if c['pass'])
    assert passing == sorted(HAND), f'passing {passing} != hand map {sorted(HAND)}'
    assert len(passing) == 26, f'passing: {len(passing)}'

    with open(LAYER) as f:
        data = json.load(f)
    before = len(data['features'])
    existing = {(f['properties']['pano_lat'], f['properties']['pano_lon'])
                for f in data['features']}

    added = []
    for n in passing:
        q, c = queue[n], check[n]
        key = (q['lat'], q['lon'])
        assert key not in existing, f'#{n} already in layer'
        name, road, faces = HAND[n]
        props = {
            'faces': faces,
            'heading': c['heading'],
            'imagery': c['imagery'],
            'name': name,
            'pano_lat': q['lat'],
            'pano_lon': q['lon'],
            'pano_note': c['notes'],
            'photosphere': False,
            'road': road,
            'trail_lat': q['lat'],
            'trail_lon': q['lon'],
            'url': ('https://www.google.com/maps/@?api=1&map_action=pano'
                    f'&viewpoint={q["lat"]:.5f},{q["lon"]:.5f}'
                    f'&heading={c["heading"]}&pitch=0'),
            'verified': True,
            'why': q['point'],
        }
        feat = {'geometry': {'coordinates': [q['lon'], q['lat']], 'type': 'Point'},
                'properties': props, 'type': 'Feature'}
        data['features'].append(feat)
        added.append(n)

    with open(LAYER, 'w') as f:
        f.write(json.dumps(data, sort_keys=True, separators=(',', ':')))

    # verify from disk
    with open(LAYER) as f:
        again = json.load(f)
    assert len(again['features']) == before + 26 == 56, len(again['features'])
    coords = [(f['properties']['pano_lat'], f['properties']['pano_lon'])
              for f in again['features']]
    assert len(set(coords)) == len(coords), 'duplicate coords'
    for f in again['features'][before:]:
        assert f['geometry']['type'] == 'Point'
        assert f['properties'].get('verified') is True
    assert all(f['geometry']['type'] == 'Point' for f in again['features'])
    print(f'OK: {before} -> {len(again["features"])} features; added #{", #".join(map(str, added))}')


if __name__ == '__main__':
    main()

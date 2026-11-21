#!/usr/bin/env python3
"""Facing-directions pass for photo batch 5 (Nov 20, 2026).

Recreates the Nov 18 post-build pass (scripts/add_directions.py, lost
with /tmp) for the 18 NEW pins of batch 5 only. Never touches the 127
carried-over pins.

Method (from data/assets/flags-report-batch3.md, "Post-build addendum —
facing directions"): no photo in the batch carries EXIF camera direction,
so every facing is inferred from the GPX track's bearing at the photo's
matched time — front photos face the direction of travel, back photos
the opposite (bearing + 180 deg), detail photos carry no direction
(facing unknowable for a punch-in). Inferred directions are marked
direction_ref "track" so they are never mistaken for a phone compass
reading. Degrees to 1 decimal; compass is the 16-point wind.

Bearing rule: the bearing of the track segment bracketing the photo's
time (same interpolation as photo_pipeline.match_gpx). If that segment
is shorter than 2 m (photographer pausing), the window widens to
interpolated positions at t-20s / t+20s, then t-60s / t+60s, then
t-180s / t+180s, until the displacement reaches 2 m; the widest window
used is reported per photo. Pin-level direction_deg / direction_ref /
direction_compass are copied from the pin's front photo.

Usage: python3 scripts/add_directions_batch5.py
Writes data/assets/assets.geojson and site/data/assets.geojson in place.
"""

import bisect
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = __file__.rsplit("/", 2)[0]
GPX = REPO + "/working/photos-inbox-2026-11-20/Nov_20,_2026,_3_00_48_PM.gpx"
DATA = REPO + "/data/assets/assets.geojson"
SITE = REPO + "/site/data/assets.geojson"
TZ = ZoneInfo("America/Chicago")

COMPASS16 = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass16(degrees):
    if degrees is None:
        return None
    return COMPASS16[int((degrees % 360.0) / 22.5 + 0.5) % 16]


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, degrees clockwise from N."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = (math.cos(p1) * math.sin(p2)
         - math.sin(p1) * math.cos(p2) * math.cos(dl))
    return math.degrees(math.atan2(x, y)) % 360.0


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def read_track(path):
    """Return [(epoch, lat, lon), ...] from the GPX trkpt elements only."""
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    root = ET.parse(path).getroot()
    pts = []
    for el in root.findall(".//g:trkpt", ns):
        t = el.find("g:time", ns)
        pts.append((datetime.fromisoformat(t.text.replace("Z", "+00:00"))
                    .timestamp(),
                    float(el.get("lat")), float(el.get("lon"))))
    pts.sort()
    return pts


def interp_pos(track, epoch):
    """Linearly interpolated (lat, lon) at epoch; None outside the span."""
    times = [p[0] for p in track]
    if epoch < times[0] or epoch > times[-1]:
        return None
    i = bisect.bisect_left(times, epoch)
    if i < len(times) and times[i] == epoch:
        return track[i][1], track[i][2]
    if i == 0 or i >= len(times):
        return None
    t0, la0, lo0 = track[i - 1]
    t1, la1, lo1 = track[i]
    if t1 - t0 > 120:  # do not interpolate across a tracker gap
        return None
    frac = (epoch - t0) / (t1 - t0)
    return la0 + frac * (la1 - la0), lo0 + frac * (lo1 - lo0)


def travel_bearing(track, epoch):
    """Bearing of travel at epoch. Returns (bearing, window_s, note).

    Primary: the bearing of the track segment bracketing the photo's
    time. If that segment is shorter than 2 m (photographer pausing),
    widen to interpolated positions at t-half / t+half for half in
    (20, 60, 180) s, clamping to the track ends when the photo sits
    near the start or end of the track.
    """
    times = [p[0] for p in track]
    i = bisect.bisect_left(times, epoch)
    if 0 < i < len(times):
        t0, la0, lo0 = track[i - 1]
        t1, la1, lo1 = track[i]
        if haversine_m(la0, lo0, la1, lo1) >= 2.0:
            return bearing_deg(la0, lo0, la1, lo1), 0, ""
    for half in (20, 60, 180):
        a = interp_pos(track, epoch - half)
        b = interp_pos(track, epoch + half)
        if a is None:
            a = (track[0][1], track[0][2])
        if b is None:
            b = (track[-1][1], track[-1][2])
        if haversine_m(a[0], a[1], b[0], b[1]) >= 2.0:
            return bearing_deg(a[0], a[1], b[0], b[1]), half, ""
    return None, 180, "no 2 m displacement within +/-180 s"


def main():
    track = read_track(GPX)
    print(f"track: {len(track)} points")
    with open(DATA) as fh:
        data = json.load(fh)
    new_pins = [f for f in data["features"]
                if "20261120" in json.dumps(f["properties"].get("photos", []))]
    print(f"new pins: {len(new_pins)}")
    counts = {"front": 0, "back": 0, "detail": 0, "unresolved": 0}
    widened = []
    for feat in new_pins:
        props = feat["properties"]
        assert props["direction_deg"] is None, props["photo"]
        for ph in props["photos"]:
            dt = datetime.strptime(ph["datetime"], "%Y:%m:%d %H:%M:%S")
            epoch = dt.replace(tzinfo=TZ).timestamp()
            role = ph["role"]
            if role == "detail":
                ph["direction_deg"] = None
                ph["direction_ref"] = None
                ph["direction_compass"] = None
                counts["detail"] += 1
                continue
            brg, half, note = travel_bearing(track, epoch)
            if brg is None:
                ph["direction_deg"] = None
                ph["direction_ref"] = None
                ph["direction_compass"] = None
                counts["unresolved"] += 1
                print(f"  UNRESOLVED {ph['photo']}: {note}")
                continue
            if role == "back":
                brg = (brg + 180.0) % 360.0
            ph["direction_deg"] = round(brg, 1)
            ph["direction_ref"] = "track"
            ph["direction_compass"] = compass16(brg)
            counts[role] += 1
            if half:
                widened.append((ph["photo"], half))
        front = props["photos"][0]
        assert front["role"] == "front", props["photo"]
        props["direction_deg"] = front["direction_deg"]
        props["direction_ref"] = front["direction_ref"]
        props["direction_compass"] = front["direction_compass"]
    print(f"inferred: front={counts['front']} back={counts['back']} "
          f"detail_null={counts['detail']} unresolved={counts['unresolved']}")
    for name, half in widened:
        print(f"  widened to +-{half}s: {name}")
    with open(DATA, "w") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")
    # Mirror into the published copy: same 18 pins, same edits.
    with open(SITE) as fh:
        site = json.load(fh)
    by_photo = {}
    for feat in data["features"]:
        by_photo[feat["properties"]["photo"]] = feat["properties"]
    for feat in site["features"]:
        src = by_photo.get(feat["properties"]["photo"])
        if src is not None and "20261120" in json.dumps(
                feat["properties"].get("photos", [])):
            feat["properties"] = src
    with open(SITE, "w") as fh:
        json.dump(site, fh, indent=1)
        fh.write("\n")
    print("wrote", DATA, "and", SITE)


if __name__ == "__main__":
    main()

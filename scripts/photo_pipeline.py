#!/usr/bin/env python3
"""Photo -> pin pipeline for the chapter asset inventory.

Two modes:

  check  Pre-flight / batch checker. Reads EXIF only (stdlib only, no
         third-party imports): per photo, reports filename, GPS
         yes/no, lat/lon, datetime, and camera direction (GPS
         ImgDirection) when the photo carries a valid one; and per
         photographer (when the folder is arranged in per-person
         subfolders) a green/red summary: green = photos carry GPS,
         red = none do.

  build  Emit data/assets/assets.geojson (one Point per photo WITH
         GPS; pins carry direction_deg / direction_ref /
         direction_compass, null when the photo has no valid camera
         direction) plus a web-sized derivative per photo in
         site/assets-photos/, and data/assets/flags-report.md listing
         no-GPS photos, oversize refusals and duplicate
         datetime+coordinate pairs. Photos with GPS but no valid
         direction are noted in the flags report (informational).

         Build MERGES with the existing assets.geojson: pins already
         in the file are carried over untouched (type, condition,
         serial and attached photos survive), and only photos not
         yet known get fresh pins. A photo is known if it is a pin's
         primary photo or listed in a pin's `photos` array, so
         re-running a batch whose duplicates were collapsed cannot
         resurrect them as separate pins.

         Every pin carries `serial: null` and `sign_kind: null` —
         build NEVER assigns a serial. Serials are assigned at
         classification by the separate editorial step
         scripts/assign_serials.py (ITM-<type>-<nnn> per
         data/assets/registry.json; docs/asset-serial-numbers-2026-11-11.md).
         Build also stamps `chainage_mi` / `section` / `snap_m`
         from the depicted chain (build_gazetteer's snap machinery;
         a pin snapping further than 250 m from the chain is
         off-chain and keeps chainage/section null) — the chainage
         is what the assign step orders by, west to east. If the
         chain files cannot be read, build still succeeds and leaves
         those three fields null (the assign step derives them then).

Storage rule (DESIGN.md, "Standing rule — photo storage split"):
original photos NEVER enter the repo; only web derivatives do. The
pipeline refuses to emit any single derivative over 5 MB and logs the
refusal in the flags report.

Dependencies: `check` needs only the Python standard library.
`build` additionally needs Pillow, and only to resize derivatives;
if Pillow is missing it still writes the GeoJSON and flags the
missing derivatives rather than failing the run.

Usage:
  python3 scripts/photo_pipeline.py check PHOTOS_DIR [--gpx TRACK.gpx]
  python3 scripts/photo_pipeline.py build PHOTOS_DIR [--gpx TRACK.gpx]
        [--out-dir DIR] [--assets-name NAME] [--derivatives DIR]
        [--flags-name NAME]

GPX matching (Paul, Nov 11, 2026): photos from a phone that writes
NO GPS (the standing case — see docs/photo-protocol.md) are placed
by matching the photo's EXIF timestamp to the track log's nearest
points. EXIF datetimes are camera-local time, read as
America/Chicago unless --tz says otherwise; GPX times are UTC.
A photo matches only inside the track's time span and only where
its two bracketing track points are at most MAX_TRACK_GAP_S apart
(a paused tracker leaves a gap the interpolation must not bridge);
the position is linearly interpolated by time between those two
points, and the pin records gps_source="gpx" plus gpx_offset_s
(seconds to the nearest track point) so a matched position is
never mistaken for a device fix. Photos with EXIF GPS keep it
(gps_source="exif"); photos with neither are excluded as before.
"""

import argparse
import bisect
import hashlib
import json
import os
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:                          # pragma: no cover
    ZoneInfo = None

MAX_OUTPUT_BYTES = 5 * 1024 * 1024          # storage rule: refuse > 5 MB outputs
DERIVATIVE_MAX_EDGE = 1600                  # web derivative: max px on long edge
PHOTO_EXTS = {".jpg", ".jpeg"}
DEFAULT_TZ = "America/Chicago"              # EXIF datetimes are camera-local
MAX_TRACK_GAP_S = 120                       # bracketing points this far apart
                                            # mean the tracker was paused:
                                            # do not interpolate across it

# ---------------------------------------------------------------- EXIF (stdlib)

def _find_exif_tiff(data):
    """Locate the TIFF header inside a JPEG's APP1 EXIF segment.
    Returns the absolute offset of the TIFF header, or None."""
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            return None
        marker = data[pos + 1]
        if marker == 0xDA:                      # start of scan: stop
            return None
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if length < 2:
            return None
        if marker == 0xE1 and data[pos + 4:pos + 10] == b"Exif\x00\x00":
            return pos + 10
        pos += 2 + length
    return None


class _Tiff:
    """Minimal read-only TIFF/EXIF reader over a bytes buffer."""

    TYPES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8}

    def __init__(self, data, base):
        self.data = data
        self.base = base                        # offset of TIFF header in data
        endian = data[base:base + 2]
        self.fmt = "<" if endian == b"II" else ">"
        self.u16 = lambda o: struct.unpack_from(self.fmt + "H", data, o)[0]
        self.u32 = lambda o: struct.unpack_from(self.fmt + "I", data, o)[0]

    def ifd(self, offset):
        """offset is TIFF-relative. Returns {tag: (type, count, value_offset)}."""
        entries = {}
        abs_off = self.base + offset
        if abs_off + 2 > len(self.data):
            return entries
        count = self.u16(abs_off)
        for i in range(count):
            e = abs_off + 2 + i * 12
            if e + 12 > len(self.data):
                break
            tag = self.u16(e)
            typ = self.u16(e + 2)
            num = self.u32(e + 4)
            entries[tag] = (typ, num, e + 8)    # value-or-offset field position
        return entries

    def value(self, entry):
        """Decode an entry to bytes/str/int/float/list-of-rationals per type."""
        typ, num, fieldpos = entry
        size = self.TYPES.get(typ, 1) * num
        if size <= 4:
            raw = self.data[fieldpos:fieldpos + size]
        else:
            off = self.base + self.u32(fieldpos)
            raw = self.data[off:off + size]
        if typ == 2:                            # ASCII
            return raw.split(b"\x00")[0].decode("ascii", "replace")
        if typ == 3:
            return list(struct.unpack(self.fmt + "H" * num, raw[:2 * num]))
        if typ == 4:
            return list(struct.unpack(self.fmt + "I" * num, raw[:4 * num]))
        if typ in (5, 10):                      # rational / srational
            fmt = "II" if typ == 5 else "ii"
            out = []
            for i in range(num):
                n, d = struct.unpack_from(self.fmt + fmt, raw, i * 8)
                out.append(n / d if d else 0.0)
            return out
        if typ == 1:
            return list(raw[:num])
        return raw


COMPASS16 = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass16(degrees):
    """16-wind compass name for a bearing in degrees (0 = N, clockwise).
    Returns None for None input."""
    if degrees is None:
        return None
    return COMPASS16[int((degrees % 360.0) / 22.5 + 0.5) % 16]


def read_exif(path):
    """Return {'lat': float|None, 'lon': float|None, 'datetime': str|None,
    'gps': bool, 'direction': float|None, 'direction_ref': str|None}.
    'direction' is the camera's facing (EXIF GPS ImgDirection, degrees
    0-360) and 'direction_ref' its north reference ('T' true / 'M'
    magnetic); both are None unless a valid direction is present —
    see the validity rule where the GPS IFD is parsed.
    Parses JPEG EXIF with the standard library only."""
    result = {"lat": None, "lon": None, "datetime": None, "gps": False,
              "direction": None, "direction_ref": None}
    with open(path, "rb") as f:
        data = f.read(2 * 1024 * 1024)          # EXIF lives in the header area
    base = _find_exif_tiff(data)
    if base is None:
        return result
    try:
        tiff = _Tiff(data, base)
        ifd0 = tiff.ifd(tiff.u32(base + 4))
        if 0x8769 in ifd0:                      # EXIF IFD: DateTimeOriginal
            exif = tiff.ifd(tiff.u32(ifd0[0x8769][2]))   # value field holds the IFD offset
            if 0x9003 in exif:
                result["datetime"] = tiff.value(exif[0x9003])
        if result["datetime"] is None and 0x0132 in ifd0:
            result["datetime"] = tiff.value(ifd0[0x0132])
        if 0x8825 in ifd0:                      # GPS IFD
            gps = tiff.ifd(tiff.u32(ifd0[0x8825][2]))
            if 0x0002 in gps and 0x0004 in gps:
                lat = tiff.value(gps[0x0002])   # [deg, min, sec] rationals
                lon = tiff.value(gps[0x0004])
                lat_ref = tiff.value(gps[0x0001]) if 0x0001 in gps else "N"
                lon_ref = tiff.value(gps[0x0003]) if 0x0003 in gps else "E"
                if len(lat) == 3 and len(lon) == 3:
                    la = lat[0] + lat[1] / 60.0 + lat[2] / 3600.0
                    lo = lon[0] + lon[1] / 60.0 + lon[2] / 3600.0
                    if isinstance(lat_ref, str) and lat_ref.startswith("S"):
                        la = -la
                    if isinstance(lon_ref, str) and lon_ref.startswith("W"):
                        lo = -lo
                    if la != 0.0 or lo != 0.0:
                        result["lat"] = round(la, 7)
                        result["lon"] = round(lo, 7)
                        result["gps"] = True
                        # Camera direction (GPS ImgDirection 0x0011 +
                        # ImgDirectionRef 0x0010). Validity: the ref
                        # must be 'T' (true north) or 'M' (magnetic),
                        # the value a single rational in [0, 360), and
                        # the position must not itself be the zero
                        # template — a direction is only read here,
                        # under result["gps"], so one riding on a
                        # zeroed-template GPS block (zero
                        # lat/lon, empty refs — e.g. a phone that never
                        # got a fix: its ImgDirection sits at 0.0 with
                        # an empty ref) is treated as absent.
                        if 0x0011 in gps:
                            dir_ref = (tiff.value(gps[0x0010])
                                       if 0x0010 in gps else None)
                            dir_val = tiff.value(gps[0x0011])
                            if (isinstance(dir_val, (list, tuple))
                                    and len(dir_val) == 1
                                    and isinstance(dir_ref, str)
                                    and dir_ref.strip().upper() in ("T", "M")
                                    and 0.0 <= dir_val[0] < 360.0):
                                result["direction"] = round(
                                    float(dir_val[0]), 1)
                                result["direction_ref"] = \
                                    dir_ref.strip().upper()
    except (struct.error, IndexError, ZeroDivisionError):
        pass
    return result


# ---------------------------------------------------------------- GPX matching

def _localname(tag):
    return tag.rsplit("}", 1)[-1]


def load_gpx(path):
    """Parse a GPX track file. Returns a sorted list of
    (epoch_seconds_utc, lat, lon). Stdlib only; namespace-agnostic."""
    tree = ET.parse(path)
    pts = []
    for el in tree.getroot().iter():
        if _localname(el.tag) != "trkpt":
            continue
        lat = el.get("lat")
        lon = el.get("lon")
        when = None
        for child in el:
            if _localname(child.tag) == "time":
                when = (child.text or "").strip()
                break
        if lat is None or lon is None or not when:
            continue
        try:
            dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        pts.append((dt.timestamp(), float(lat), float(lon)))
    pts.sort()
    return pts


def parse_exif_datetime(s):
    """'2026:11:11 11:33:53' -> naive datetime, or None."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _tzinfo(name):
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    # No tz database available: fixed offsets for the zones this
    # project uses (America/Chicago is UTC-6 in standard time,
    # Nov–Mar; the trail batches are shot in that window).
    from datetime import timedelta
    if name == "America/Chicago":
        return timezone(timedelta(hours=-6))
    return timezone.utc


def match_gpx(track, dt_local, tz_name=DEFAULT_TZ,
              max_gap_s=MAX_TRACK_GAP_S):
    """Match a camera-local datetime to the track. Returns
    {'lat', 'lon', 'offset_s', 'gap_s'} or None.
    offset_s = seconds to the nearest bracketing track point;
    gap_s = seconds between the two bracketing points."""
    if not track or dt_local is None:
        return None
    tz = _tzinfo(tz_name)
    epoch = dt_local.replace(tzinfo=tz).timestamp()
    times = [p[0] for p in track]
    if epoch < times[0] or epoch > times[-1]:
        return None
    i = bisect.bisect_left(times, epoch)
    if i < len(times) and times[i] == epoch:
        _t, la, lo = track[i]
        return {"lat": round(la, 7), "lon": round(lo, 7),
                "offset_s": 0.0, "gap_s": 0.0}
    if i == 0 or i >= len(times):
        return None
    t0, la0, lo0 = track[i - 1]
    t1, la1, lo1 = track[i]
    gap = t1 - t0
    if gap > max_gap_s:
        return None
    frac = (epoch - t0) / gap if gap else 0.0
    return {"lat": round(la0 + frac * (la1 - la0), 7),
            "lon": round(lo0 + frac * (lo1 - lo0), 7),
            "offset_s": round(min(epoch - t0, t1 - epoch), 1),
            "gap_s": round(gap, 1)}


# ---------------------------------------------------------------- shared scan

def scan_photos(root):
    """Walk root; return list of dicts: path, rel, photographer
    (immediate subfolder name, or None for files at the top level)."""
    found = []
    root = os.path.abspath(root)
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() not in PHOTO_EXTS:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            parts = rel.split(os.sep)
            photographer = parts[0] if len(parts) > 1 else None
            found.append({"path": full, "rel": rel, "filename": name,
                          "photographer": photographer})
    return found


def slugify(name):
    stem = os.path.splitext(name)[0].lower()
    out = []
    for ch in stem:
        out.append(ch if (ch.isalnum() or ch in "-_") else "-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "photo"


# ---------------------------------------------------------------- check mode

def cmd_check(args):
    photos = scan_photos(args.photos_dir)
    track = load_gpx(args.gpx) if getattr(args, "gpx", None) else None
    if track:
        from datetime import timezone as _tz
        span = (datetime.fromtimestamp(track[0][0], _tz.utc).isoformat(),
                datetime.fromtimestamp(track[-1][0], _tz.utc).isoformat())
        print(f"GPX track: {len(track)} points, {span[0]} to {span[1]} UTC")
    rows = []
    matched = 0
    for p in photos:
        ex = read_exif(p["path"])
        m = None
        if not ex["gps"] and track:
            m = match_gpx(track, parse_exif_datetime(ex["datetime"]),
                          tz_name=getattr(args, "tz", DEFAULT_TZ))
            if m:
                matched += 1
        rows.append({**p, **ex, "match": m})
        if ex["gps"]:
            gps_txt = "yes"
            coords = f"{ex['lat']:.6f}, {ex['lon']:.6f}"
        elif m:
            gps_txt = "gpx"
            coords = (f"{m['lat']:.6f}, {m['lon']:.6f} "
                      f"(+{m['offset_s']:.0f}s)")
        else:
            gps_txt = "no"
            coords = "-"
        if ex.get("direction") is not None:
            dir_txt = (f"{ex['direction']:.0f}° "
                       f"{compass16(ex['direction'])} "
                       f"({ex['direction_ref']})")
        else:
            dir_txt = "-"
        print(f"{p['rel']}\tGPS: {gps_txt}\t{coords}\t"
              f"{ex['datetime'] or '-'}\tDir: {dir_txt}")
    by_person = {}
    for r in rows:
        by_person.setdefault(r["photographer"], []).append(r)
    print("\n--- per-photographer summary ---")
    for person in sorted(by_person, key=lambda x: (x is None, x or "")):
        rs = by_person[person]
        with_gps = sum(1 for r in rs if r["gps"])
        label = person if person is not None else "(top level, no subfolder)"
        if with_gps == 0:
            status = "RED"
        elif with_gps == len(rs):
            status = "GREEN"
        else:
            status = "GREEN (partial)"
        print(f"{label}: {status} — {with_gps}/{len(rs)} photos with GPS")
    total_gps = sum(1 for r in rows if r["gps"])
    total_match = sum(1 for r in rows if r.get("match"))
    print(f"\nTotal: {len(rows)} photos scanned, {total_gps} with EXIF GPS, "
          f"{total_match} matched to the GPX track, "
          f"{len(rows) - total_gps - total_match} without a position.")
    return 0


# ---------------------------------------------------------------- build mode

def make_derivative(src, dest):
    """Write a web derivative (max DERIVATIVE_MAX_EDGE px long edge).
    Returns size in bytes. Raises if Pillow is unavailable."""
    from PIL import Image
    im = Image.open(src)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.thumbnail((DERIVATIVE_MAX_EDGE, DERIVATIVE_MAX_EDGE))
    im.save(dest, "JPEG", quality=82)
    return os.path.getsize(dest)


def cmd_build(args):
    photos = scan_photos(args.photos_dir)
    out_dir = args.out_dir
    if args.derivatives:
        deriv_dir = os.path.abspath(args.derivatives)
    else:
        # Default: <repo>/site/assets-photos, derived from this
        # script's location — NOT from out_dir (out_dir is
        # <repo>/data/assets, so ".." from it lands in data/).
        repo_root = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        deriv_dir = os.path.join(repo_root, "site", "assets-photos")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(deriv_dir, exist_ok=True)

    # MERGE (Nov 11, 2026 — protects classified/serialized pins):
    # build no longer rewrites the inventory from scratch. Pins
    # already in <out_dir>/assets.geojson are carried over untouched
    # (type, condition, serial, attached photos), and only photos
    # not yet known get fresh pins. A photo is known if it is a
    # pin's primary photo or listed in a pin's `photos` array, so
    # re-running a batch whose duplicates were collapsed cannot
    # resurrect them. A corrupt existing file fails loudly instead
    # of being clobbered.
    _assets_path = os.path.join(out_dir, args.assets_name)
    existing_features = []
    known_photos = set()
    if os.path.exists(_assets_path):
        with open(_assets_path) as _f:
            _existing = json.load(_f)
        existing_features = _existing.get("features", [])
        for _feat in existing_features:
            _props = _feat.get("properties", {})
            if _props.get("photo"):
                known_photos.add(_props["photo"])
            for _ph in _props.get("photos", []):
                if _ph.get("photo"):
                    known_photos.add(_ph["photo"])
        print(f"merge: {len(existing_features)} existing pins carried "
              f"over ({len(known_photos)} known photos)")
    scanned_total = len(photos)
    carried = [p for p in photos if p["filename"] in known_photos]
    photos = [p for p in photos if p["filename"] not in known_photos]
    if carried:
        print(f"merge: {len(carried)} photos already known — skipped")

    features = []
    no_gps = []
    no_direction = []
    refusals = []
    deriv_notes = []
    seen_keys = {}
    duplicates = []

    track = load_gpx(args.gpx) if getattr(args, "gpx", None) else None
    gpx_name = os.path.basename(args.gpx) if track else None
    if track:
        print(f"GPX track: {len(track)} points from {gpx_name}")
    matched = 0
    max_offset = 0.0

    used_slugs = set()
    for p in photos:
        ex = read_exif(p["path"])
        m = None
        if not ex["gps"] and track:
            m = match_gpx(track, parse_exif_datetime(ex["datetime"]),
                          tz_name=getattr(args, "tz", DEFAULT_TZ))
        if not ex["gps"] and not m:
            no_gps.append(p)
            continue
        if m:
            matched += 1
            max_offset = max(max_offset, m["offset_s"])
            lat, lon = m["lat"], m["lon"]
            gps_source = "gpx"
            gpx_offset = m["offset_s"]
        else:
            lat, lon = ex["lat"], ex["lon"]
            gps_source = "exif"
            gpx_offset = None
        if ex.get("direction") is None:
            no_direction.append(p)
        slug = slugify(p["filename"])
        if p["photographer"]:
            slug = slugify(p["photographer"]) + "-" + slug
        base_slug, n = slug, 2
        while slug in used_slugs:
            slug = f"{base_slug}-{n}"
            n += 1
        used_slugs.add(slug)
        deriv_name = slug + ".jpg"
        deriv_path = os.path.join(deriv_dir, deriv_name)

        key = (ex["datetime"], lat, lon)
        if key in seen_keys:
            duplicates.append((seen_keys[key], p))
        else:
            seen_keys[key] = p

        deriv_rel = None
        try:
            size = make_derivative(p["path"], deriv_path)
            if size > MAX_OUTPUT_BYTES:
                os.remove(deriv_path)
                refusals.append((p, f"derivative {size} bytes > {MAX_OUTPUT_BYTES}"))
            else:
                deriv_rel = deriv_name
        except ImportError:
            deriv_notes.append((p, "Pillow not installed — derivative not written"))
        except Exception as exc:                # unreadable image etc.
            deriv_notes.append((p, f"derivative failed: {exc}"))

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "photo": p["filename"],
                "datetime": ex["datetime"],
                "photographer": p["photographer"],
                "type": "unclassified",
                "condition": None,
                "drive_id": None,
                "derivative": deriv_rel,
                "direction_deg": ex.get("direction"),
                "direction_ref": ex.get("direction_ref"),
                "direction_compass": compass16(ex.get("direction")),
                # Position provenance: "exif" (device fix) or "gpx"
                # (timestamp-interpolated from the track log).
                # gpx_offset_s is seconds to the nearest track
                # point; a matched position is an estimate, never
                # a device fix.
                "gps_source": gps_source,
                "gpx_offset_s": gpx_offset,
                "gpx_file": gpx_name,
                # Serials are assigned at classification, never here
                # (scripts/assign_serials.py). sign_kind is null
                # unless the pin is classified as a sign (SG).
                "serial": None,
                "sign_kind": None,
                # Chainage along the depicted chain, stamped below.
                "chainage_mi": None,
                "section": None,
                "snap_m": None,
            },
        })

    # Stamp chainage / section / snap distance from the depicted
    # chain (the same snap machinery build_gazetteer.py uses; a pin
    # further than 250 m from the chain is off-chain and keeps
    # chainage/section null). Guarded: if the chain files cannot be
    # read, build still succeeds and the assign step derives these.
    chain_ok = False
    snapped = 0
    off_chain = []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import build_gazetteer as _gaz
        _stretches = _gaz.load(
            "data/segments/segment-stretches.geojson")["features"]
        _gaps = _gaz.load("data/segments/gaps.geojson")["features"]
        _pieces, _total = _gaz.build_chain(_stretches, _gaps)
        chain_ok = True
        for feat in features:
            lon, lat = feat["geometry"]["coordinates"]
            piece, ch, snap = _gaz.project(_pieces, [lon, lat])
            props = feat["properties"]
            props["snap_m"] = round(float(snap), 2)
            if snap > _gaz.SNAP_LIMIT_M:
                off_chain.append((props["photo"], props["snap_m"]))
            else:
                props["chainage_mi"] = round(float(ch), 2)
                props["section"] = piece.name
                snapped += 1
    except Exception as exc:                # chain unreadable: no chainage
        print(f"chainage unavailable ({exc}) — chainage_mi/section "
              f"left null; assign_serials.py will derive them",
              file=sys.stderr)

    collection = {"type": "FeatureCollection",
                  "features": existing_features + features}
    assets_path = os.path.join(out_dir, args.assets_name)
    with open(assets_path, "w") as f:
        json.dump(collection, f, indent=1)
        f.write("\n")
    assets_size = os.path.getsize(assets_path)
    # The viewer reads the site copy (site/data/assets.geojson);
    # the pipeline writes it alongside the repo copy so a build
    # never needs a manual copy step.
    try:
        repo_root = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        site_copy = os.path.join(repo_root, "site", "data",
                                 args.assets_name)
        os.makedirs(os.path.dirname(site_copy), exist_ok=True)
        shutil.copyfile(assets_path, site_copy)
        print(f"wrote site copy {site_copy}")
    except Exception as exc:
        print(f"site copy not written ({exc})", file=sys.stderr)
    if assets_size > MAX_OUTPUT_BYTES:
        refusals.append(({"rel": args.assets_name}, f"geojson {assets_size} bytes"))

    lines = ["# Photo pipeline — flags report",
             f"\nGenerated {datetime.now().isoformat(timespec='seconds')} "
             f"from `{args.photos_dir}`.",
             f"\nScanned {scanned_total} photos: {len(features)} new "
             f"positioned ({len(features) - matched} EXIF GPS, "
             f"{matched} GPX-matched), {len(no_gps)} without a position "
             f"(excluded); {len(carried)} already known, carried over "
             f"untouched. {len(existing_features) + len(features)} pins "
             f"total in the file.",
             "\n## GPX matching\n"]
    if track:
        from datetime import timezone as _tz
        span = (datetime.fromtimestamp(track[0][0], _tz.utc).isoformat(),
                datetime.fromtimestamp(track[-1][0], _tz.utc).isoformat())
        lines.append(f"Track file: `{gpx_name}` — {len(track)} points, "
                     f"{span[0]} to {span[1]} UTC; EXIF datetimes read as "
                     f"{getattr(args, 'tz', DEFAULT_TZ)} local time; "
                     f"bracketing-point gap limit {MAX_TRACK_GAP_S} s.\n")
        lines.append(f"{matched} photos matched to the track (largest "
                     f"offset to the nearest track point: "
                     f"{max_offset:.0f} s); "
                     f"{len(no_gps)} photos had no usable match and were "
                     f"excluded — listed under 'No position' below. "
                     f"Matched pins carry gps_source=\"gpx\" and "
                     f"gpx_offset_s; they are time-interpolated "
                     f"estimates, not device fixes.\n")
    else:
        lines.append("No GPX track given — positions came from EXIF GPS "
                     "only.\n")
    lines.append("\n## No position — excluded from the map\n")
    if no_gps:
        for p in no_gps:
            who = p["photographer"] or "(top level)"
            lines.append(f"- {p['rel']} — photographer: {who}")
    else:
        lines.append("- none")
    lines.append("\n## GPS but no camera direction (informational)\n")
    lines.append("These photos carry GPS and were pinned, but no valid "
                 "EXIF camera direction (GPS ImgDirection) — their pins "
                 "have null direction fields. Not an error.\n")
    if no_direction:
        for p in no_direction:
            who = p["photographer"] or "(top level)"
            lines.append(f"- {p['rel']} — photographer: {who}")
    else:
        lines.append("- none")
    lines.append("\n## Chainage along the trail\n")
    if not chain_ok:
        lines.append("Chain files unreadable at build time — chainage_mi / "
                     "section left null on all pins; assign_serials.py "
                     "derives them when it runs.\n")
    else:
        lines.append(f"{snapped} pins snapped to the depicted chain "
                     f"(chainage_mi + section stamped); "
                     f"{len(off_chain)} off-chain (> 250 m — chainage / "
                     f"section null).\n")
        for photo, snap_m in off_chain:
            lines.append(f"- {photo} — snap {snap_m} m")
    lines.append("\n## Oversize refusals (> 5 MB output)\n")
    if refusals:
        for p, why in refusals:
            lines.append(f"- {p.get('rel', '?')}: {why}")
    else:
        lines.append("- none")
    lines.append("\n## Duplicates (same datetime + coordinates)\n")
    if duplicates:
        for first, dup in duplicates:
            lines.append(f"- {dup['rel']} duplicates {first['rel']}")
    else:
        lines.append("- none")
    if deriv_notes:
        lines.append("\n## Derivative notes\n")
        for p, note in deriv_notes:
            lines.append(f"- {p['rel']}: {note}")
    flags_path = os.path.join(out_dir, args.flags_name)
    with open(flags_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"scanned={scanned_total} with_gps={len(features)} "
          f"exif={len(features) - matched} gpx_matched={matched} "
          f"max_offset_s={max_offset:.0f} no_gps={len(no_gps)} "
          f"duplicates={len(duplicates)} "
          f"refusals={len(refusals)} snapped={snapped} "
          f"off_chain={len(off_chain)} carried={len(carried)} "
          f"total_pins={len(existing_features) + len(features)}")
    print(f"wrote {assets_path}")
    print(f"wrote {flags_path}")
    print(f"derivatives in {deriv_dir}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("check", help="EXIF check (pre-flight protocol)")
    c.add_argument("photos_dir")
    c.add_argument("--gpx", default=None,
                   help="GPX track file: match photos without EXIF GPS "
                        "to the track by timestamp")
    c.add_argument("--tz", default=DEFAULT_TZ,
                   help="timezone EXIF datetimes are read as "
                        f"(default: {DEFAULT_TZ})")
    c.set_defaults(fn=cmd_check)
    b = sub.add_parser("build", help="build assets.geojson + derivatives + flags")
    b.add_argument("photos_dir")
    b.add_argument("--gpx", default=None,
                   help="GPX track file: match photos without EXIF GPS "
                        "to the track by timestamp")
    b.add_argument("--tz", default=DEFAULT_TZ,
                   help="timezone EXIF datetimes are read as "
                        f"(default: {DEFAULT_TZ})")
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.normpath(os.path.join(here, "..", "data", "assets"))
    b.add_argument("--out-dir", default=default_out)
    b.add_argument("--assets-name", default="assets.geojson")
    b.add_argument("--flags-name", default="flags-report.md")
    b.add_argument("--derivatives", default=None,
                   help="derivative folder (default: <repo>/site/assets-photos)")
    b.set_defaults(fn=cmd_build)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

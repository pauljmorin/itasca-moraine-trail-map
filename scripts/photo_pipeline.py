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

Storage rule (DESIGN.md, "Standing rule — photo storage split"):
original photos NEVER enter the repo; only web derivatives do. The
pipeline refuses to emit any single derivative over 5 MB and logs the
refusal in the flags report.

Dependencies: `check` needs only the Python standard library.
`build` additionally needs Pillow, and only to resize derivatives;
if Pillow is missing it still writes the GeoJSON and flags the
missing derivatives rather than failing the run.

Usage:
  python3 scripts/photo_pipeline.py check PHOTOS_DIR
  python3 scripts/photo_pipeline.py build PHOTOS_DIR [--out-dir DIR]
        [--assets-name NAME] [--derivatives DIR] [--flags-name NAME]
"""

import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import datetime

MAX_OUTPUT_BYTES = 5 * 1024 * 1024          # storage rule: refuse > 5 MB outputs
DERIVATIVE_MAX_EDGE = 1600                  # web derivative: max px on long edge
PHOTO_EXTS = {".jpg", ".jpeg"}

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
    rows = []
    for p in photos:
        ex = read_exif(p["path"])
        rows.append({**p, **ex})
        gps_txt = "yes" if ex["gps"] else "no"
        coords = (f"{ex['lat']:.6f}, {ex['lon']:.6f}" if ex["gps"] else "-")
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
    print(f"\nTotal: {len(rows)} photos scanned, {total_gps} with GPS, "
          f"{len(rows) - total_gps} without.")
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
    deriv_dir = args.derivatives or os.path.join(out_dir, "..", "site", "assets-photos")
    deriv_dir = os.path.abspath(deriv_dir)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(deriv_dir, exist_ok=True)

    features = []
    no_gps = []
    no_direction = []
    refusals = []
    deriv_notes = []
    seen_keys = {}
    duplicates = []

    used_slugs = set()
    for p in photos:
        ex = read_exif(p["path"])
        if not ex["gps"]:
            no_gps.append(p)
            continue
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

        key = (ex["datetime"], ex["lat"], ex["lon"])
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
            "geometry": {"type": "Point", "coordinates": [ex["lon"], ex["lat"]]},
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
            },
        })

    collection = {"type": "FeatureCollection", "features": features}
    assets_path = os.path.join(out_dir, args.assets_name)
    with open(assets_path, "w") as f:
        json.dump(collection, f, indent=1)
    assets_size = os.path.getsize(assets_path)
    if assets_size > MAX_OUTPUT_BYTES:
        refusals.append(({"rel": args.assets_name}, f"geojson {assets_size} bytes"))

    lines = ["# Photo pipeline — flags report",
             f"\nGenerated {datetime.now().isoformat(timespec='seconds')} "
             f"from `{args.photos_dir}`.",
             f"\nScanned {len(photos)} photos: {len(features)} with GPS "
             f"(pins written), {len(no_gps)} without GPS (excluded).",
             "\n## No GPS — excluded from the map\n"]
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

    print(f"scanned={len(photos)} with_gps={len(features)} "
          f"no_gps={len(no_gps)} duplicates={len(duplicates)} "
          f"refusals={len(refusals)}")
    print(f"wrote {assets_path}")
    print(f"wrote {flags_path}")
    print(f"derivatives in {deriv_dir}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("check", help="EXIF check (pre-flight protocol)")
    c.add_argument("photos_dir")
    c.set_defaults(fn=cmd_check)
    b = sub.add_parser("build", help="build assets.geojson + derivatives + flags")
    b.add_argument("photos_dir")
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

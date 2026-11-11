#!/usr/bin/env python3
"""Assign asset serial numbers (editorial step — never automatic).

Serials are assigned at classification, not at photo intake:
scripts/photo_pipeline.py build always writes `serial: null`, and
this is the only script that stamps a serial onto a pin. Run it
after a classification batch has set `type` on the pins to number
(Muse proposes, Paul approves — the standing rule that editing runs
through Paul holds for serials too, since a serial once published
can never be taken back).

Format (Paul, 2026-11-11): ITM-<type>-<nnn> — chapter prefix, the
type code from data/assets/registry.json, zero-padded three-digit
sequence per type (grows to four digits past 999). See
docs/asset-serial-numbers-2026-11-11.md for the rules this
implements:

* Only classified pins are numbered: type must be a registry code
  or name (matched case-insensitively against the registry's `types`
  table — codes are what pins carry, names are accepted for
  hand-built pins); `unclassified` pins and the UN bucket never get
  a serial. A serial held as RESERVED in the issued map is skipped,
  not minted (docs/asset-serial-numbers-2026-11-11.md §3 rule 7).
* A type with no counter yet (a "proposed" code being used for the
  first time) opens its counter at 001 — the code itself must
  already be in the registry's types table; an unknown type name
  fails loudly instead of inventing a code.
* Ordering within a batch: chainage order, west to east. Pins that
  snap to the depicted chain (snap_m <= 250 m, the gazetteer's
  SNAP_LIMIT_M) sort by chainage_mi; pins that cannot be snapped
  (off-corridor, or no chainage yet) are numbered after the snapped
  ones, in file order. Pins missing chainage_mi get it derived here
  from the same snap machinery build_gazetteer.py uses, when the
  chain files are readable.
* Never reuse, never renumber: each assignment advances the
  registry counter and records the serial in `issued`. This script
  never touches an existing serial and never retires one — retiring
  is a manual registry edit with a reason.

Usage:
  python3 scripts/assign_serials.py [--assets PATH]
        [--registry PATH] [--dry-run]
"""

import argparse
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SNAP_LIMIT_M = 250.0  # same limit as build_gazetteer.SNAP_LIMIT_M


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def serial_for(code, n):
    return "ITM-%s-%03d" % (code, n)


def snap_chainage(lon, lat):
    """(chainage_mi, section, snap_m) via build_gazetteer's chain, or
    (None, None, None) when the chain files cannot be read."""
    try:
        sys.path.insert(0, HERE)
        import build_gazetteer as gaz
        stretches = gaz.load("data/segments/segment-stretches.geojson")[
            "features"]
        gaps = gaz.load("data/segments/gaps.geojson")["features"]
        pieces, _total = gaz.build_chain(stretches, gaps)
        piece, ch, snap = gaz.project(pieces, [lon, lat])
        if snap > SNAP_LIMIT_M:
            return None, None, round(snap, 2)
        return round(float(ch), 2), piece.name, round(snap, 2)
    except Exception:
        return None, None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assets", default=os.path.join(
        ROOT, "data", "assets", "assets.geojson"))
    ap.add_argument("--registry", default=os.path.join(
        ROOT, "data", "assets", "registry.json"))
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be assigned; write nothing")
    args = ap.parse_args()

    registry = load_json(args.registry)
    types = registry.get("types", {})
    counters = registry.setdefault("counters", {})
    # code or name (lowercased) -> code, for the pin type values.
    # Pins carry the two-letter CODE ("BW", "CP", "SG"); names are
    # accepted too ("boardwalk", "sign") for hand-built pins. The
    # UN bucket is excluded either way — it never gets a serial.
    by_name = {code.lower(): code for code, v in types.items()
               if v.get("status") != "bucket"}
    by_name.update({v["name"].lower(): code for code, v in types.items()
                    if v.get("status") != "bucket"
                    and v.get("name")})

    collection = load_json(args.assets)
    features = collection.get("features", [])

    # Candidates: classified pins with no serial yet.
    candidates = []
    problems = []
    for i, feat in enumerate(features):
        props = feat.get("properties", {})
        if props.get("serial"):
            continue  # already numbered — never touched
        t = (props.get("type") or "").strip()
        if not t or t.lower() in ("unclassified", "un"):
            continue  # unclassified pins carry no serial
        code = by_name.get(t.lower())
        if code is None:
            problems.append(
                "%s (type %r is not in the registry types table — "
                "a new type needs its two-letter code approved and "
                "added to data/assets/registry.json first)"
                % (props.get("photo") or "feature %d" % i, t))
            continue
        candidates.append((i, feat, code))

    if problems:
        for p in problems:
            print("ERROR: " + p, file=sys.stderr)
        print("assignment aborted: fix the pins above first",
              file=sys.stderr)
        return 1

    # Chainage for ordering: use the stored value when present,
    # else derive it now (and keep it on the pin).
    for _i, feat, _code in candidates:
        props = feat["properties"]
        if props.get("chainage_mi") is None:
            lon, lat = feat["geometry"]["coordinates"]
            ch, section, snap = snap_chainage(lon, lat)
            props["chainage_mi"] = ch
            if section is not None:
                props["section"] = section
            if snap is not None:
                props["snap_m"] = snap
    # Snapped pins first, in chainage order; unsnapped after, in
    # file order (the sort is stable, so file order is preserved).
    candidates.sort(key=lambda c: (
        c[1]["properties"].get("chainage_mi") is None,
        c[1]["properties"].get("chainage_mi")
        if c[1]["properties"].get("chainage_mi") is not None else 0.0))

    if not candidates:
        print("nothing to assign: no classified, unnumbered pins")
        return 0

    today = date.today().isoformat()
    assigned = []
    for _i, feat, code in candidates:
        props = feat["properties"]
        counter = counters.setdefault(
            code, {"next": 1, "issued": {}, "retired": []})
        n = counter["next"]
        # A serial already in the issued map with a "reserved" marker
        # (held for an item not yet classified, e.g. the unreadable
        # paper notice) is skipped, not minted and not an error. Any
        # other collision means the counter is behind its issued map
        # — a real inconsistency, still fatal.
        while True:
            serial = serial_for(code, n)
            existing = counter.get("issued", {}).get(serial)
            if existing is None:
                break
            if existing.get("reserved"):
                n += 1
                continue
            print("ERROR: %s already issued — registry counter for %s "
                  "is behind its issued map; fix registry.json by hand"
                  % (serial, code), file=sys.stderr)
            return 1
        counter["next"] = n + 1
        counter.setdefault("issued", {})[serial] = {
            "photo": props.get("photo"),
            "type": code,
            "chainage_mi": props.get("chainage_mi"),
            "section": props.get("section"),
            "assigned": today,
        }
        if props.get("drive_id"):
            counter["issued"][serial]["drive_id"] = props["drive_id"]
        if not args.dry_run:
            props["serial"] = serial
        assigned.append((serial, props.get("photo"),
                         props.get("chainage_mi"), props.get("section")))

    for serial, photo, ch, section in assigned:
        where = ("chainage %s mi" % ch) if ch is not None \
            else "off-chain / unsnapped"
        print("%s <- %s (%s%s)" % (
            serial, photo, where,
            (", " + section) if section else ""))

    if args.dry_run:
        print("dry run: nothing written (%d would be assigned)"
              % len(assigned))
    else:
        save_json(args.assets, collection)
        save_json(args.registry, registry)
        print("wrote %s (%d pins numbered)" % (args.assets, len(assigned)))
        print("wrote %s" % args.registry)
    return 0


if __name__ == "__main__":
    sys.exit(main())

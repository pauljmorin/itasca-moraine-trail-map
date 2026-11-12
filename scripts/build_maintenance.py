#!/usr/bin/env python3
"""Build the maintenance inventory as a data file (Nov 11, 2026).

The maintenance inventory (Paul, Nov 11: a SEPARATE inventory from
the assets, deliberately) becomes a real GeoJSON file so the panel
work list and the map layer can never disagree — both render from
this one file.

Source: the batch-2 maintenance list
(working/photos-inbox-2026-11-11-batch2/maintenance-2026-11-11-batch2.md)
plus the batch-1 failing item ITM-PO-001. Coordinates and photo
derivatives resolve from the asset pins in data/assets/assets.geojson
(by photo filename), so an item's position is the pin's position —
never a re-typed lat/lon. Items that are also real assets keep their
asset pin and serial; the cross-reference rides the `asset` field.

Severity: "soon" (needs work soon) or "wait" (can wait). Nothing
graded urgent: no structure is failing.

Outputs (identical): data/maintenance.geojson (source of truth) and
site/data/maintenance.geojson (the site copy). Run after any
maintenance-list change; the script validates every photo
derivative exists and every named asset serial is in the registry.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# id, title, fix (one plain sentence), severity, chainage_mi,
# section, asset serial (or None), photo filenames (primary first).
ITEMS = [
    ("M-001", "Shot-up sign", "Replace the sign board — face unreadable",
     "soon", 57.26, "Chip-5", "ITM-SG-016",
     ["PXL_20261111_171222895.jpg"]),
    ("M-002", "Blowdown", "Saw and clear — tread blocked",
     "soon", 57.35, "Chip-5", None,
     ["PXL_20261111_171417596.MP.jpg"]),
    ("M-003", "Blowdown", "Saw and clear — tread blocked",
     "soon", 57.46, "Chip-5", None,
     ["PXL_20261111_171622584.MP.jpg"]),
    ("M-004", "Blowdown", "Saw and clear — tread blocked",
     "soon", 57.47, "Chip-5", None,
     ["PXL_20261111_171633870.jpg"]),
    ("M-005", "Blowdown", "Saw and clear — tread blocked",
     "soon", 57.50, "Chip-5", None,
     ["PXL_20261111_171740292.MP.jpg",
      "PXL_20261111_171741627.jpg"]),
    ("M-006", "Blowdown", "Saw and clear — tread blocked",
     "soon", 57.54, "Chip-5", None,
     ["PXL_20261111_171840137.MP.jpg"]),
    ("M-007", "Limb on the marsh bridge",
     "Clear the limb — bridge itself is sound",
     "soon", None, "Lake Erin Loop", "ITM-BR-002",
     ["PXL_20261111_164313064.jpg",
      "PXL_20261111_164324579.MP.jpg",
      "PXL_20261111_164336858.MP.jpg"]),
    ("M-008", "Raised board end", "Refasten the board — trip hazard",
     "soon", 58.21, "Chip-5", "ITM-BW-009",
     ["PXL_20261111_173347090.jpg"]),
    ("M-009", "Leaning post", "Replace the post — leaning, split base",
     "soon", 58.36, "Chip-5", "ITM-PO-001",
     ["PXL_20261111_173913740.jpg"]),
    ("M-010", "Loose plank",
     "Check whether it belongs to the run; refasten or replace",
     "wait", 56.54, "Chip-5", "ITM-BW-008",
     ["PXL_20261111_165051063.MP.jpg"]),
    ("M-011", "Wet tread dip",
     "Monitor; consider a puncheon if it worsens",
     "wait", None, "Lake Erin Loop", None,
     ["PXL_20261111_164249781.jpg",
      "PXL_20261111_164253208.jpg"]),
    ("M-012", "Beaver-gnawed tree",
     "Watch in case it falls across the trail",
     "wait", None, "Lake Erin Loop", None,
     ["PXL_20261111_164303475.jpg"]),
]


def main():
    assets = json.load(open(os.path.join(
        ROOT, "data", "assets", "assets.geojson")))
    by_photo = {}
    serials = set()
    for f in assets["features"]:
        p = f["properties"] or {}
        if p.get("serial"):
            serials.add(p["serial"])
        for ph in p.get("photos") or []:
            by_photo[ph.get("photo")] = (f, ph)
        if p.get("photo"):
            by_photo.setdefault(p["photo"], (f, None))

    features = []
    errors = []
    for (mid, title, fix, sev, ch, section, asset, photos) in ITEMS:
        if asset and asset not in serials:
            errors.append("%s: asset serial %s not in the registry"
                          % (mid, asset))
        coords = None
        derivatives = []
        for ph in photos:
            hit = by_photo.get(ph)
            if not hit:
                errors.append("%s: photo %s has no asset pin" % (mid, ph))
                continue
            feat, _ = hit
            if coords is None:
                coords = feat["geometry"]["coordinates"]
            # derivative for this exact photo, from the pin's array
            deriv = None
            for pp in feat["properties"].get("photos") or []:
                if pp.get("photo") == ph:
                    deriv = pp.get("derivative")
            if not deriv:
                errors.append("%s: no derivative for %s" % (mid, ph))
                continue
            if not os.path.exists(os.path.join(
                    ROOT, "site", "assets-photos", deriv)):
                errors.append("%s: derivative missing on disk: %s"
                              % (mid, deriv))
            derivatives.append(deriv)
        if coords is None:
            errors.append("%s: no coordinates resolved" % mid)
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": coords},
            "properties": {
                "id": mid, "title": title, "fix": fix,
                "severity": sev, "chainage_mi": ch,
                "section": section, "asset": asset,
                "photos": derivatives,
                "photo": derivatives[0] if derivatives else None,
            },
        })

    if errors:
        for e in errors:
            print("ERROR: " + e, file=sys.stderr)
        return 1

    fc = {"type": "FeatureCollection", "features": features}
    for path in (os.path.join(ROOT, "data", "maintenance.geojson"),
                 os.path.join(ROOT, "site", "data", "maintenance.geojson")):
        with open(path, "w") as f:
            json.dump(fc, f, indent=1)
            f.write("\n")
    soon = sum(1 for f in features
               if f["properties"]["severity"] == "soon")
    wait = len(features) - soon
    print("wrote %d maintenance items (%d needs work soon, %d can wait)"
          % (len(features), soon, wait))
    print("  data/maintenance.geojson")
    print("  site/data/maintenance.geojson")
    return 0


if __name__ == "__main__":
    sys.exit(main())

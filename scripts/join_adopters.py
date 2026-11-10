#!/usr/bin/env python3
"""Join the chapter adoption tracker onto the KMZ segment geometry.

Inputs
  data/segments/adopters-2026-09.xlsx     the chapter's tracker
      (system of record for adopters/assignments; "September 2026"
      edition, current as of 2026-11-10)
  data/segments/segments.geojson          KMZ boundary pins (output of
                                          scripts/segment_overlay.py)
  data/segments/segment-stretches.geojson KMZ-derived adopted stretches

Outputs (same two GeoJSONs, enriched in place)
  * tracker fields joined per segment where the match is defensible:
    exact section-name match after normalization (WEST-n -> West-n,
    CHP-n -> Chip-n), plus the tracker-only split of WEST-8 into
    WEST-8A / WEST-8B (the KMZ has one West-8 stretch; it is split at
    the chainage implied by the tracker's virtual-mile proportion)
  * /tmp/adopters_join_stats.json — inventory, join hit rate,
    unmatched rows on both sides, and every comparison the report's
    "Tracker vs KMZ" section uses

Privacy: the tracker carries phone numbers and email addresses.
Those columns are NEVER copied into any output; only names, section
descriptions, mile markers, map references, lengths, sawyer,
comments and the 2026 maintenance notes are joined.  The joined
files are chapter working-view data.

Run AFTER scripts/segment_overlay.py (it consumes that script's
outputs; it does not redo any geometry except the WEST-8 split).
"""

import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_util
from segment_overlay import build_chains, from_xy, hav_mi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, "data/segments/adopters-2026-09.xlsx")
SEGMENTS = os.path.join(ROOT, "data/segments/segments.geojson")
STRETCHES = os.path.join(ROOT, "data/segments/segment-stretches.geojson")
OFFICIAL = os.path.join(ROOT, "data/segments/official-line-chapter-extent.geojson")
OUT_STATS = "/tmp/adopters_join_stats.json"
TRACKER_SOURCE = "adopters-2026-09.xlsx (chapter tracker, Sept 2026 edition)"


def clean(v):
    """Normalize a spreadsheet cell to a single-line string (or None)."""
    if v is None:
        return None
    s = str(v).replace("\xa0", " ").replace("_x000B_", " ")
    s = re.sub(r"\s*\n\s*", "\n", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s or None


def clean1(v):
    s = clean(v)
    return s.replace("\n", " ") if s else None


def parse_people(v):
    """Split an adopter/sawyer cell into individual names."""
    s = clean(v)
    if not s:
        return []
    out = []
    for chunk in re.split(r"\n|,", s):
        for part in chunk.split(" & "):
            p = part.strip(" .")
            if p:
                out.append(p)
    return out


def norm_section(name):
    """Tracker section name -> KMZ-style segment name (or None)."""
    s = (name or "").strip().upper()
    m = re.match(r"^WEST-(\d+)([AB])?$", s)
    if m:
        return "West-%d%s" % (int(m.group(1)), (m.group(2) or "").lower())
    m = re.match(r"^CHP-(\d+)$", s)
    if m:
        return "Chip-%d" % int(m.group(1))
    return None  # e.g. 'Waboose' — a named loop, no KMZ counterpart name


def load_tracker(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    stats = {"sheets": {}}
    adopters = []
    ws = wb["Adopters"]
    stats["sheets"]["Adopters"] = {
        "dimensions": ws.dimensions,
        "title_row": clean1(ws["A1"].value),
        "columns": [clean1(c.value) for c in ws[2]],
        "hyperlink_cells": sum(1 for row in ws.iter_rows() for c in row
                               if c.hyperlink),
        "footnote": clean1(ws["B35"].value)}
    for row in ws.iter_rows(min_row=3, max_row=34):
        vals = [c.value for c in row]
        if vals[0] is None:
            continue
        length = vals[5]
        adopters.append({
            "section_raw": clean1(vals[0]),
            "section": norm_section(vals[0]),
            "description": clean1(vals[1]),
            "is_loop": clean1(vals[3]) == "Loop",
            "mile_start": vals[2] if isinstance(vals[2], (int, float))
            else clean1(vals[2]),
            "mile_end": vals[3] if isinstance(vals[3], (int, float))
            else clean1(vals[3]),
            "map_refs": [p for p in re.split(r"[\n ]+", clean(vals[4]) or "")
                         if p.startswith("MN-")],
            "length_mi": float(length) if isinstance(length, (int, float))
            else float(clean1(length)),
            "adopter": parse_people(vals[6]),
            "adopter_verbatim": clean1(vals[6]),
            "sawyer": clean1(vals[9]),
            "comments": clean1(vals[10]),
            "_has_phone": bool(clean(vals[7])),
            "_has_email": bool(clean(vals[8]))})
    stats["adopters_rows"] = len(adopters)
    stats["adopters_with_phone"] = sum(1 for a in adopters if a["_has_phone"])
    stats["adopters_with_email"] = sum(1 for a in adopters if a["_has_email"])
    for a in adopters:
        del a["_has_phone"], a["_has_email"]

    ml = []
    ws = wb["Maintenance Log"]
    stats["sheets"]["Maintenance Log"] = {
        "dimensions": ws.dimensions,
        "columns": [clean1(c.value) for c in ws[1]],
        "note": "Columns A/B are live array formulas mirroring the "
                "Adopters sheet ('Adopters'!A/B); C and D are this "
                "sheet's own content. Column E is empty."}
    for row in ws.iter_rows(min_row=2, max_row=33):
        vals = [c.value for c in row]
        if vals[0] is None:
            continue
        helpv = vals[3]
        ml.append({
            "section_raw": clean1(vals[0]),
            "section": norm_section(vals[0]),
            "adopter": parse_people(vals[1]),
            "notes_2026": clean1(vals[2]),
            "help_raw": helpv if isinstance(helpv, (int, float))
            else clean1(helpv)})
    stats["maintenance_rows"] = len(ml)
    return adopters, ml, stats


def split_polyline_at(coords, target_mi):
    """Split a lonlat polyline at target distance from its start.
    Returns (coords_a, coords_b, achieved_mi)."""
    acc = 0.0
    for i, (a, b) in enumerate(zip(coords, coords[1:])):
        seg = hav_mi(a, b)
        if acc + seg >= target_mi:
            t = 0.0 if seg == 0 else (target_mi - acc) / seg
            ax, ay = geo_util.to_xy(a)
            bx, by = geo_util.to_xy(b)
            mid = from_xy((ax + t * (bx - ax), ay + t * (by - ay)))
            return (coords[:i + 1] + [list(mid)],
                    [list(mid)] + coords[i + 1:], target_mi)
        acc += seg
    return coords, [], acc


def main():
    adopters, mlog, stats = load_tracker(XLSX)
    by_section = {a["section"]: a for a in adopters if a["section"]}
    ml_by_section = {m["section"]: m for m in mlog if m["section"]}
    waboose = next(a for a in adopters if a["section_raw"] == "Waboose")

    stretches = json.load(open(STRETCHES))
    segments = json.load(open(SEGMENTS))
    official = json.load(open(OFFICIAL))
    itm = [f for f in official["features"]
           if f["properties"].get("chapter") == "ITM"]
    chains, _ = build_chains(itm)
    chain = chains[0]

    # ---------------- split the KMZ West-8 stretch into 8A / 8B
    split_info = None
    feats = stretches["features"]
    for i, f in enumerate(feats):
        p = f["properties"]
        if p["name"] != "West-8":
            continue
        a_sec, b_sec = by_section["West-8a"], by_section["West-8b"]
        total_tracker = a_sec["length_mi"] + b_sec["length_mi"]
        frac = a_sec["length_mi"] / total_tracker
        target = p["length_mi"] * frac
        coords = [tuple(c) for c in f["geometry"]["coordinates"]]
        ca, cb, achieved = split_polyline_at(coords, target)
        boundary_cha = p["chainage_start_mi"] + achieved

        def part(sec, cs, ce, cgeo, part_of):
            accs = []
            for a in p["access_points"]:
                d = a["dist_from_start_mi"] - (cs - p["chainage_start_mi"])
                if not (cs - p["chainage_start_mi"] - 0.26 <= a["dist_from_start_mi"]
                        <= ce - p["chainage_start_mi"] + 0.26):
                    continue
                a2 = dict(a)
                a2["dist_from_start_mi"] = round(
                    min(max(d, 0.0), ce - cs), 3)
                a2["position"] = ("start" if a2["dist_from_start_mi"] <= 0.25
                                  else "end" if (ce - cs) - a2["dist_from_start_mi"] <= 0.25
                                  else "mid")
                accs.append(a2)
            has_s = any(a["position"] == "start" for a in accs)
            has_e = any(a["position"] == "end" for a in accs)
            has_m = any(a["position"] == "mid" for a in accs)
            return {"type": "Feature",
                    "geometry": {"type": "LineString",
                                 "coordinates": [[c[0], c[1]] for c in cgeo]},
                    "properties": dict(
                        p,
                        name=sec["section"], from_boundary=p["from_boundary"],
                        to_boundary=("West-9" if sec is b_sec else "West-8b (Island Lake Sign)"),
                        part_of=part_of,
                        chainage_start_mi=round(cs, 4),
                        chainage_end_mi=round(ce, 4),
                        length_mi=round(ce - cs, 3),
                        offroad_mi=round(p["offroad_mi"] * (ce - cs) / p["length_mi"], 3),
                        onroad_mi=round(p["onroad_mi"] * (ce - cs) / p["length_mi"], 3),
                        access_points=accs,
                        access_at_start=has_s, access_at_end=has_e,
                        single_ended_access=(has_s != has_e) and not has_m,
                        both_ends_access=has_s and has_e,
                        no_end_access_but_mid=(not has_s) and (not has_e) and has_m)}

        part_a = part(a_sec, p["chainage_start_mi"], boundary_cha, ca, "West-8")
        part_b = part(b_sec, boundary_cha, p["chainage_end_mi"], cb, "West-8")
        feats[i:i + 1] = [part_a, part_b]
        split_info = {"parent": "West-8",
                      "boundary_chainage_mi": round(boundary_cha, 4),
                      "boundary_lonlat": [round(cb[0][0], 6), round(cb[0][1], 6)],
                      "method": "tracker virtual-mile proportion "
                                "(2.25 / 4.75 of the KMZ stretch length)",
                      "part_lengths_mi": [part_a["properties"]["length_mi"],
                                          part_b["properties"]["length_mi"]]}
        break
    stats["west8_split"] = split_info

    # ---------------- join tracker fields onto stretches
    joined, unmatched_tracker, length_rows = [], [], []
    for f in feats:
        p = f["properties"]
        sec = by_section.get(p["name"])
        if sec is None:
            p["tracker_match"] = False
            continue
        ml = ml_by_section.get(p["name"], {})
        p["tracker_match"] = True
        p["tracker_section"] = sec["section_raw"]
        p["tracker_description"] = sec["description"]
        p["adopter"] = sec["adopter"]
        p["adopter_verbatim"] = sec["adopter_verbatim"]
        p["sawyer"] = sec["sawyer"]
        p["tracker_comments"] = sec["comments"]
        p["nct_mile_start"] = sec["mile_start"]
        p["nct_mile_end"] = sec["mile_end"]
        p["nct_map_refs"] = sec["map_refs"]
        p["tracker_length_mi"] = sec["length_mi"]
        p["maintenance_2026_notes"] = ml.get("notes_2026")
        p["help_requested_2026_raw"] = ml.get("help_raw")
        p["status"] = ("adopted — tracker section %s (adopter of record "
                       "in %s)" % (sec["section_raw"], TRACKER_SOURCE))
        joined.append(p["name"])
        if not sec["is_loop"]:
            length_rows.append({
                "section": sec["section_raw"], "kmz_name": p["name"],
                "tracker_mi": sec["length_mi"],
                "kmz_mi": p["length_mi"],
                "diff_mi": round(p["length_mi"] - sec["length_mi"], 3)})
    kmz_names = {f["properties"]["name"] for f in feats}
    for a in adopters:
        if a["section"] and a["section"] not in kmz_names:
            unmatched_tracker.append(a["section_raw"])
    stats["join"] = {
        "tracker_sections": len(adopters),
        "tracker_sections_named_like_kmz": len(by_section),
        "stretches_after_split": len(feats),
        "joined_stretches": len(joined),
        "joined_names": joined,
        "unmatched_tracker_sections": unmatched_tracker,
        "unmatched_kmz_stretches": [f["properties"]["name"] for f in feats
                                    if not f["properties"].get("tracker_match")]}
    stats["length_comparison"] = length_rows
    stats["length_diffs_over_0.3"] = [r for r in length_rows
                                      if abs(r["diff_mi"]) > 0.3]

    # tracker-internal adopter consistency (Adopters vs Maintenance Log)
    mism = []
    for name, a in by_section.items():
        m = ml_by_section.get(name)
        if m and set(a["adopter"]) != set(m["adopter"]):
            mism.append({"section": name,
                         "adopters_sheet": a["adopter"],
                         "maintenance_log": m["adopter"]})
    stats["tracker_internal_adopter_mismatches"] = mism
    stats["sections_without_adopter"] = [
        a["section_raw"] for a in adopters if not a["adopter"]]
    stats["tracker_totals"] = {
        "adopters_sheet_mainline_mi": round(sum(
            a["length_mi"] for a in adopters if not a["is_loop"]), 3),
        "loop_sections": [{"section": a["section_raw"],
                           "stated_mi": a["length_mi"],
                           "adopter": a["adopter"]}
                          for a in adopters if a["is_loop"]],
        "virtual_span": [min(a["mile_start"] for a in adopters
                             if isinstance(a["mile_start"], (int, float))),
                         max(a["mile_end"] for a in adopters
                             if isinstance(a["mile_end"], (int, float)))]}

    # ---------------- join onto the boundary pins (segments.geojson)
    pin_joined = []
    for f in segments["features"]:
        p = f["properties"]
        sec = by_section.get(p["name"])
        p["tracker_match"] = bool(sec)
        if sec:
            ml = ml_by_section.get(p["name"], {})
            p["tracker_section"] = sec["section_raw"]
            p["tracker_description"] = sec["description"]
            p["adopter"] = sec["adopter"]
            p["sawyer"] = sec["sawyer"]
            p["tracker_length_mi"] = sec["length_mi"]
            p["nct_mile_start"] = sec["mile_start"]
            p["nct_mile_end"] = sec["mile_end"]
            p["maintenance_2026_notes"] = ml.get("notes_2026")
            pin_joined.append(p["name"])
        if p["name"] == "West-14":
            p["waboose_note"] = (
                "The tracker's Waboose Lake Loop section (4 mi, "
                "adopters: %s) branches from this pin's NCT mile "
                "(201.75) — the same marker where WEST-14 begins. The "
                "KMZ has no separate Waboose pin; the pin's West-14 "
                "placement at the Waboose junction is consistent "
                "with the tracker's structure."
                % ", ".join(waboose["adopter"]))
    stats["pin_join"] = {"joined_pins": pin_joined,
                         "joined_count": len(pin_joined)}

    # ---------------- targeted concordance checks
    junction = chain.point_at(44.9798)
    stats["checks"] = {
        "west9_west10_lag": {
            "tracker_boundary_miles": ["WEST-9 190.5-194.0",
                                       "WEST-10 loop at 192-194",
                                       "WEST-11 starts 194.0"],
            "kmz_pin_chainages_mi": {"West-9": 23.8555, "West-10": 25.8012,
                                     "West-11": 27.4665},
            "finding": "the WEST-10 loop section sits INSIDE WEST-9's "
                       "mile span in the tracker, and there is no "
                       "room for it between the West-10 and West-11 "
                       "KMZ pins (1.67 mi of mainline) — the KMZ West "
                       "pins run ~2 NCT miles behind the tracker's "
                       "boundaries through this stretch (see report)"},
        "waboose_loop_geometry": {
            "pin": list(waboose_pin) if (waboose_pin := (-94.812295, 47.062032)) else None,
            "finding": "no closed loop exists in the official line "
                       "near the West-14 pin: the two ITM features "
                       "passing it are ordinary mainline (endpoint "
                       "separations 1.01 and 0.72 mi vs lengths 1.20 "
                       "and 1.10 mi). The 4-mile Waboose Lake Loop is "
                       "not in the official depiction."},
        "junction_county_line": {
            "point": [round(junction[0], 6), round(junction[1], 6)],
            "finding": "WEST-17 ends at the 'Cass Co. Line' and CHP-1 "
                       "begins at the 'Cass/Hubbard Co. Line' — the "
                       "tracker and the KMZ series junction agree "
                       "that the West/Chip handover sits at this pin "
                       "(KMZ Chip-1). Project data carries no county-"
                       "boundary layer to verify the line itself."}}

    stretches["metadata"]["tracker_join"] = (
        "Adopter/section fields joined from %s by "
        "scripts/join_adopters.py. Phone/email columns were NOT "
        "copied. WEST-8 split into WEST-8A/8B per the tracker." % TRACKER_SOURCE)
    segments["metadata"]["tracker_join"] = (
        "Tracker fields for the segment starting at each pin, joined "
        "from %s by scripts/join_adopters.py (names/descriptions "
        "only; no contact details)." % TRACKER_SOURCE)
    json.dump(stretches, open(STRETCHES, "w"), indent=1)
    json.dump(segments, open(SEGMENTS, "w"), indent=1)
    json.dump(stats, open(OUT_STATS, "w"), indent=1, default=str)
    print(json.dumps({k: stats[k] for k in
                      ("adopters_rows", "maintenance_rows", "join",
                       "west8_split", "tracker_totals",
                       "sections_without_adopter",
                       "tracker_internal_adopter_mismatches")}, indent=1))


if __name__ == "__main__":
    main()

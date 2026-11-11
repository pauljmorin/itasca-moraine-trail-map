#!/usr/bin/env python3
"""Build the gazetteer index for the map site: site/data/gazetteer.geojson.

A search index of named things on the chapter's trail — sections,
section boundaries, the chapter termini, the computed road/trail
crossings, and the NCTA public waypoints (parking, camping,
shelters, water, points of interest) — each entry a point carrying
its position along the depicted chain in two mileages:

* chainage_mi — miles along the depicted chain from its west end
  (the GAP-W west end in Itasca State Park, chainage 0);
* nct_mile — the NCT "virtual mile" of the tracker's calibration:
  each stretch declares nct_mile_start/end (segment-stretches
  .geojson); a point inside a stretch is interpolated between that
  stretch's declared pair by its chainage fraction, and a point in
  GAP-W is interpolated 166.58 -> 169.5 across the gap (169.5 is
  West-1's declared start; 166.58 = 169.5 - the gap's 2.92 mi).
  Nothing is extrapolated: a point whose chainage falls outside
  every calibrated span gets nct_mile = None.

Projection reuses the segment overlay's approach: the depicted
chain is rebuilt as the GAP-W polyline followed by the stretch
polylines in chainage order (data/segments/), and a point's
position is its nearest point on that chain, converted to anchor
chainage through the piece it lands in (so published chainages are
preserved exactly, not re-measured). Points off the chain snap to
their nearest chain point; the snap distance is recorded (snap_m).

SECTION RECORDS carry the adoption tracker's content under the
field rules in site/README.md ("Spreadsheet fields"): description,
NCT map refs, virtual miles, 2026 maintenance notes, the raw
Help Requested values, and land context cross verbatim (after a
contact-pattern scrub — emails/phone numbers are stripped and the
strip count is printed); adopter and sawyer names cross ONLY as
the v2 placeholders ("Test adopter N", numbered exactly as
scripts/build_site_data.py numbers them, recovered here from
site/data/stretches.geojson so the two builds can never disagree;
sawyer-only people continue the same numbering); tracker comments
cross only after every known person's name has been substituted
by their placeholder — a comment that still contains an unmatched
personal reference is dropped (working data keeps it verbatim) and
the drop is counted and printed. Phone/email columns never leave
the working data at all: they are not even read here.

Dedupe: a computed access crossing within 100 m of an NCTA parking
point is dropped in favour of the named NCTA entry (count printed).

Chapter places (data/points/chapter-places.geojson, the chapter's
own records — seeded from the NCTA camping points Nov 10, 2026,
then hand-maintained) SUPERSEDE the NCTA points they name: the
NCTA layer carries no id field, so a chapter entry's `supersedes`
is the composite key "ncta-points:<name>@<lon>,<lat>" (six
decimals, exactly as recorded in data/points/ncta-points.geojson;
see scripts/seed_chapter_places.py). A superseded NCTA waypoint is
dropped here (count printed) and the chapter entry takes its
place — source "chapter", the chapter's fields (status,
description, capacity, water note, record source) carried across —
so a place appears exactly once, as its chapter version, in the
index, in Find and in the What's-here lists. The Places map layer
skips source-"chapter" entries (the Chapter places layer draws
them from site/data/chapter-places.geojson, emitted by
scripts/build_chapter_places.py from this build's output).

Also built from site/data/boundaries.geojson (the v2 build's
points): the 32 KMZ boundary pins as "Section boundary" entries
(positions are the v2 stretch-endpoint positions, never raw pins)
and the two chapter termini as "Chapter end" entries.

Named lakes/water bodies are NOT entries: no names source for
water bodies exists in the project data (the access/roads files
name roads and trails, some of them after lakes — a road named
"Perch Lake" is a road, not the lake). Parcels are not entries
either (1,038 of them; the parcels layer is their home).

Run from the repository root:  python3 scripts/build_gazetteer.py
Inputs: data/segments/{segment-stretches,gaps}.geojson,
data/points/ncta-points.geojson,
data/points/chapter-places.geojson,
site/data/{boundaries,stretches,access-points}.geojson.
Standard library only.
"""

import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRECISION = 5

sys.path.insert(0, os.path.join(ROOT, "scripts"))
from geo_util import to_xy, dist_km  # noqa: E402  (km space)

MI_PER_KM = 0.621371192237334
GAP_NCT_START = 166.58  # 169.5 (West-1 start) - 2.92 (gap length)
DEDUPE_PARKING_M = 100.0
SNAP_LIMIT_M = 250.0

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(
    r"(\+?1[-.\s]?)?(\(\d{3}\)\s?|\d{3}[-.\s])\d{3}[-.\s]\d{4}\b")


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


def clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def scrub_contacts(text, stats):
    """Strip email/phone patterns from tracker text; count strips."""
    if not text:
        return text
    out, n1 = EMAIL_RE.subn("[removed]", text)
    out, n2 = PHONE_RE.subn("[removed]", out)
    stats["contact_strips"] += n1 + n2
    return out


# ------------------------------------------------------------ chain
class Piece:
    """One chain piece (GAP-W or one stretch) with anchor chainages."""

    def __init__(self, name, coords, c0, c1, nct0, nct1):
        self.name = name
        self.c0, self.c1 = c0, c1
        self.nct0, self.nct1 = nct0, nct1
        self.edges = []  # (a, b, geo_len_km, cum_geo_km_at_a)
        cum = 0.0
        for a, b in zip(coords, coords[1:]):
            d = dist_km(a, b)
            self.edges.append((a, b, d, cum))
            cum += d
        self.geo_km = cum

    def chainage_at(self, frac):
        return self.c0 + frac * (self.c1 - self.c0)

    def nct_at(self, chainage):
        if self.c1 <= self.c0:
            return None
        if not all(isinstance(v, (int, float))
                   for v in (self.nct0, self.nct1)):
            return None  # e.g. West-10 the loop: tracker span is not
            # a linear calibration ('Loop'), so no NCT mile is honest
        t = (chainage - self.c0) / (self.c1 - self.c0)
        return self.nct0 + t * (self.nct1 - self.nct0)


def build_chain(stretches, gaps):
    gap = gaps[0]
    g_anchor_end = min(f["properties"]["chainage_start_mi"]
                       for f in stretches)
    pieces = [Piece("GAP-W", gap["geometry"]["coordinates"],
                    0.0, g_anchor_end, GAP_NCT_START,
                    gap_nct_end(stretches))]
    for f in sorted(stretches,
                    key=lambda f: f["properties"]["chainage_start_mi"]):
        p = f["properties"]
        coords = f["geometry"]["coordinates"]
        if f["geometry"]["type"] == "MultiLineString":
            coords = coords[0]
        if len(coords) < 2:
            continue  # zero-length stretch (Chip-13): no chain piece
        pieces.append(Piece(p["name"], coords,
                            p["chainage_start_mi"], p["chainage_end_mi"],
                            p["nct_mile_start"], p["nct_mile_end"]))
    total = max(pc.c1 for pc in pieces)
    return pieces, total


def gap_nct_end(stretches):
    west1 = min(stretches, key=lambda f: f["properties"]["chainage_start_mi"])
    return west1["properties"]["nct_mile_start"]


def project(pieces, pt):
    """Nearest point on the chain: (piece, chainage_mi, snap_m)."""
    px, py = to_xy(pt)
    best = None
    for pc in pieces:
        for a, b, d_km, cum in pc.edges:
            ax, ay = to_xy(a)
            bx, by = to_xy(b)
            dx, dy = bx - ax, by - ay
            len2 = dx * dx + dy * dy
            t = 0.0 if len2 == 0 else max(
                0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len2))
            fx, fy = ax + t * dx, ay + t * dy
            dist = math.hypot(px - fx, py - fy)
            if best is None or dist < best[0]:
                frac = 0.0 if pc.geo_km == 0 else \
                    (cum + t * d_km) / pc.geo_km
                best = (dist, pc, pc.chainage_at(frac))
    dist_km_best, piece, chainage = best
    return piece, chainage, dist_km_best * 1000.0


def nct_from_chainage(pieces, chainage):
    for pc in pieces:
        if pc.c0 <= chainage <= pc.c1 and pc.c1 > pc.c0:
            return pc.nct_at(chainage)
    return None


def line_midpoint(coords):
    pts = [(c[0], c[1]) for c in coords]
    total = sum(dist_km(a, b) for a, b in zip(pts, pts[1:]))
    half, acc = total / 2.0, 0.0
    for a, b in zip(pts, pts[1:]):
        d = dist_km(a, b)
        if d > 0 and acc + d >= half:
            t = (half - acc) / d
            ax, ay = to_xy(a)
            bx, by = to_xy(b)
            fx, fy = ax + t * (bx - ax), ay + t * (by - ay)
            kx, ky = to_xy((0.0, 0.0))
            return [fx / (111.320 * math.cos(math.radians(47.0))),
                    fy / 111.195]
        acc += d
    return list(pts[len(pts) // 2])


# ------------------------------------------------------- placeholders
def recover_placeholder_map():
    """person string -> "Test adopter N", identical to the v2 site
    build: pairs each working stretch's adopter list (file order)
    with site/data/stretches.geojson's adopter_display by name."""
    working = load("data/segments/segment-stretches.geojson")["features"]
    site = {f["properties"]["name"]: f["properties"]
            for f in load("site/data/stretches.geojson")["features"]}
    mapping = {}
    for f in working:
        p = f["properties"]
        disp = (site.get(p["name"]) or {}).get("adopter_display") or []
        for person, ph in zip(p.get("adopter") or [], disp):
            mapping.setdefault(person, ph)
    return mapping


def parse_sawyer_people(raw, mapping, next_num):
    """Split a tracker sawyer cell into people; extend the mapping
    (same numbering) for sawyer-only people. Returns (display list,
    next_num). Chunks are first matched whole against known people,
    then segmented by known full names inside the chunk (the tracker
    sometimes jams two people into one cell), else taken whole."""
    if not raw:
        return [], next_num
    people = []
    for chunk in re.split(r"[/()]", raw):
        chunk = chunk.strip(" ,")
        if not chunk:
            continue
        if chunk in mapping:
            people.append(chunk)
            continue
        rest = chunk
        found = []
        for name in sorted(mapping, key=len, reverse=True):
            if len(name.split()) >= 2 and name in rest:
                found.append(name)
                rest = rest.replace(name, " ")
        if found and not rest.strip(" ,"):
            people.extend(found)
            continue
        people.append(chunk)
    display = []
    for person in people:
        if person not in mapping:
            mapping[person] = "Test adopter %d" % next_num[0]
            next_num[0] += 1
        display.append(mapping[person])
    return display, next_num


# ---------------------------------------------------------- comments
def comment_people_index(mapping):
    """(full_names, surname->persons, firstname->persons) over the
    known-people mapping keys (adopter entries + sawyer people)."""
    full = [k for k in mapping if len(k.split()) >= 2]
    by_surname, by_first = {}, {}
    for name in mapping:
        parts = name.split()
        by_first.setdefault(parts[0], []).append(name)
        if len(parts) >= 2:
            by_surname.setdefault(parts[-1], []).append(name)
    return full, by_surname, by_first


PROTECT = [("Paul Bunyan", "\x00PAULBUNYAN\x00")]


def _substitute_names(s, mapping):
    """Replace every substitutable known-person reference in s with
    its placeholder: full names (incl. possessive), "Firstname L."
    and "Firstname L" where the first name is unambiguous and the
    initial matches, unique surnames (incl. possessive/plural),
    unique first names. Returns the substituted string."""
    for phrase, token in PROTECT:
        s = s.replace(phrase, token)
    full, by_surname, by_first = comment_people_index(mapping)

    def sub(pattern, repl, s_):
        return re.sub(pattern, repl, s_, flags=re.IGNORECASE)

    for name in sorted(full, key=len, reverse=True):
        esc = re.escape(name)
        s = sub(r"\b" + esc + r"(['’]s)?\b",
                lambda m: mapping[name] + (m.group(1) or ""), s)

    def first_initial(m):
        first, initial = m.group(1), m.group(2)
        persons = by_first.get(first) or []
        if len(persons) == 1 and (
                persons[0].split()[-1].startswith(initial)
                or len(persons[0].split()) == 1):
            # surname initial matches, or the person's recorded name
            # is a bare first name (no surname on record to check)
            return mapping[persons[0]]
        return m.group(0)
    s = re.sub(r"\b([A-Z][a-z]+) ([A-Z])\.", first_initial, s)
    s = re.sub(r"\b([A-Z][a-z]+) ([A-Z])(?![\w.])", first_initial, s)
    for surname, persons in by_surname.items():
        if len(persons) == 1:
            person = persons[0]

            def surname_repl(m, person=person):
                keep = m.group(1) if m.group(1) in ("'s", "’s") else ""
                return mapping[person] + keep
            s = sub(r"\b" + re.escape(surname) + r"(['’]s|s)?\b",
                    surname_repl, s)
    for first, persons in by_first.items():
        if len(persons) == 1:
            person = persons[0]
            s = sub(r"\b" + re.escape(first) + r"(?![\w'’])",
                    lambda m: mapping[person], s)
    for phrase, token in PROTECT:
        s = s.replace(token, phrase)
    return s


def _has_residual_person_ref(s, mapping):
    """True when s still contains a personal reference the
    substitution could not resolve (ambiguous first name, a
    Firstname-Initial pattern, or a parenthesised first name)."""
    _, _, by_first = comment_people_index(mapping)
    protected = s
    for phrase, token in PROTECT:
        protected = protected.replace(phrase, token)
    for first, persons in by_first.items():
        if len(persons) != 1 and re.search(
                r"\b" + re.escape(first) + r"\b", protected):
            return True
    if re.search(r"\b[A-Z][a-z]+ [A-Z]\.", protected):
        return True
    if re.search(r"\([A-Z][a-z]+\)", protected):
        return True
    return False


def sanitize_comment(text, mapping, stats):
    """Substitute known people's names with placeholders. Returns
    the substituted comment, or None when an unmatched personal
    reference remains (the comment is then dropped from the site
    copy; the working data keeps it verbatim)."""
    if not text:
        return None
    s = _substitute_names(text, mapping)
    # tracker shorthand "@" for "at" — keeps the site's zero-"@"
    # invariant without losing the note
    if "@" in s:
        s = re.sub(r"\s*@\s*", " at ", s)
        stats["at_signs_rewritten"] += 1
    if _has_residual_person_ref(s, mapping):
        return None
    return s.strip() or None


def sanitize_names_only(text, mapping, stats):
    """Substitution WITHOUT the drop rule, for the tracker fields
    the chapter ruled public-safe as text (maintenance notes,
    descriptions): known people's names still become placeholders
    (real names never enter the site copy); an occasional
    unresolvable first name is left as recorded and counted in
    stats['name_residues'] for the build report."""
    if not text:
        return text
    s = _substitute_names(text, mapping)
    if _has_residual_person_ref(s, mapping):
        stats["name_residues"] = stats.get("name_residues", 0) + 1
    return s


# ------------------------------------------------------------- build
def r2(v):
    return None if v is None else round(float(v), 2)


def r2_or_raw(v):
    """Round numerics; pass tracker strings (e.g. 'Loop') through."""
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return v


def main():
    stats = {"contact_strips": 0, "at_signs_rewritten": 0}
    stretches = load("data/segments/segment-stretches.geojson")["features"]
    gaps = load("data/segments/gaps.geojson")["features"]
    boundaries = load("site/data/boundaries.geojson")["features"]
    access_pts = load("site/data/access-points.geojson")["features"]
    ncta = load("data/points/ncta-points.geojson")["features"]
    chapter_places = load("data/points/chapter-places.geojson")["features"]

    pieces, total_chain = build_chain(stretches, gaps)
    mapping = recover_placeholder_map()
    base_numbers = [int(v.rsplit(" ", 1)[1]) for v in mapping.values()]
    next_num = [max(base_numbers) + 1 if base_numbers else 1]
    sawyer_only_start = next_num[0]

    entries = []

    def add(name, kind, source, coord, chainage, nct, section,
            snap_m=0.0, extra=None, sections=None):
        props = {
            "name": name,
            "kind": kind,
            "source": source,
            "section": section,
            "chainage_mi": r2(chainage),
            "nct_mile": r2(nct),
            "from_west_mi": r2(chainage),
            "from_east_mi": r2(total_chain - chainage)
            if chainage is not None else None,
            "snap_m": r2(snap_m),
        }
        if sections is not None:
            props["sections"] = sections
        if extra:
            props.update(extra)
        search_bits = [name, kind, section or ""]
        if extra:
            for k in ("description", "tracker_section", "map_refs",
                      "land_context"):
                v = extra.get(k)
                if isinstance(v, list):
                    search_bits.extend(str(x) for x in v)
                elif v:
                    search_bits.append(str(v))
        props["search_text"] = " ".join(search_bits)
        entries.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(coord[0], PRECISION),
                                         round(coord[1], PRECISION)]},
            "properties": props,
        })

    # ---- section records (tracker-enriched) ----
    by_name = {}
    for f in sorted(stretches,
                    key=lambda f: f["properties"]["chainage_start_mi"]):
        p = f["properties"]
        by_name[p["name"]] = p
        coords = f["geometry"]["coordinates"]
        if f["geometry"]["type"] == "MultiLineString":
            coords = coords[0]
        mid = line_midpoint(coords) if len(coords) >= 2 else list(coords[0])
        piece, ch, snap = project(pieces, mid)
        disp_sawyer, next_num = parse_sawyer_people(
            p.get("sawyer"), mapping, next_num)
        site_stretch = {x["properties"]["name"]: x["properties"] for x in
                        load("site/data/stretches.geojson")["features"]}
        adopter_display = (site_stretch.get(p["name"]) or {}).get(
            "adopter_display")
        land = p.get("land_context") or []
        if isinstance(land, str):
            land = [land]
        land_context = ", ".join(s.strip() for s in land
                                 if s and s.strip()) or None
        comment_raw = clean(p.get("tracker_comments"))
        comment = sanitize_comment(
            scrub_contacts(comment_raw, stats), mapping, stats)
        comment_dropped = bool(comment_raw) and comment is None
        extra = {
            "tracker_section": clean(p.get("tracker_section")),
            "description": sanitize_names_only(
                scrub_contacts(clean(p.get("tracker_description")),
                               stats), mapping, stats),
            "map_refs": p.get("nct_map_refs") or None,
            "nct_mile_start": r2_or_raw(p.get("nct_mile_start")),
            "nct_mile_end": r2_or_raw(p.get("nct_mile_end")),
            "chainage_start_mi": r2(p.get("chainage_start_mi")),
            "chainage_end_mi": r2(p.get("chainage_end_mi")),
            "length_mi": r2(p.get("length_mi")),
            "tracker_length_mi": r2(p.get("tracker_length_mi")),
            "has_adopter": bool(p.get("adopter")),
            "adopter_display": adopter_display,
            "sawyer_display": disp_sawyer or None,
            "maintenance_2026": sanitize_names_only(
                scrub_contacts(clean(p.get("maintenance_2026_notes")),
                               stats), mapping, stats),
            "help_requested": p.get("help_requested_2026_raw"),
            "land_context": land_context,
            "comments": comment,
            "comments_dropped": comment_dropped,
        }
        add(p["name"], "Section", "tracker", mid, ch,
            nct_from_chainage(pieces, ch), p["name"], snap, extra)
    # GAP-W as a section record (it is a section-shaped hole)
    g = gaps[0]
    gp = g["properties"]
    mid = line_midpoint(g["geometry"]["coordinates"])
    piece, ch, snap = project(pieces, mid)
    gland = gp.get("land_context") or []
    if isinstance(gland, str):
        gland = [gland]
    add("GAP-W", "Section", "tracker", mid, ch,
        nct_from_chainage(pieces, ch), "GAP-W", snap, {
            "tracker_section": "GAP-W",
            "description": clean(gp.get("name")),
            "map_refs": None,
            "nct_mile_start": GAP_NCT_START,
            "nct_mile_end": r2(gap_nct_end(stretches)),
            "chainage_start_mi": 0.0,
            "chainage_end_mi": r2(min(
                f["properties"]["chainage_start_mi"] for f in stretches)),
            "length_mi": r2(gp.get("length_mi")),
            "tracker_length_mi": None,
            "has_adopter": False,
            "adopter_display": None,
            "sawyer_display": None,
            "maintenance_2026": None,
            "help_requested": None,
            "land_context": ", ".join(s.strip() for s in gland
                                      if s and s.strip()) or None,
            "comments": clean(gp.get("note")),
            "comments_dropped": False,
        })

    # ---- boundaries + chapter termini ----
    west_end = east_end = None
    for b in boundaries:
        bp = b["properties"]
        coord = b["geometry"]["coordinates"]
        piece, ch, snap = project(pieces, coord)
        nct = nct_from_chainage(pieces, ch)
        sections = bp.get("sections") or []
        if bp.get("chapter_end") and bp["name"].startswith("Chapter west"):
            west_end = (coord, ch)
            continue  # emitted as a Chapter end below, not a boundary
        if bp.get("chapter_end"):
            east_end = (coord, ch, sections)
        add(bp["name"], "Section boundary", "boundaries", coord, ch, nct,
            sections[0] if sections else piece.name, snap,
            sections=sections)
    if west_end:
        coord, ch = west_end
        add("Itasca Moraine — west end", "Chapter end", "boundaries",
            coord, 0.0, GAP_NCT_START, "GAP-W", 0.0)
    if east_end:
        coord, ch, sections = east_end
        east_nct = max(f["properties"]["nct_mile_end"] for f in stretches
                       if isinstance(f["properties"]["nct_mile_end"],
                                     (int, float)))
        add("Itasca Moraine — east end", "Chapter end", "boundaries",
            coord, total_chain, east_nct,
            sections[0] if sections else "Chip-13", 0.0)

    # ---- NCTA waypoints ----
    # The point layer covers a wider envelope than the depicted
    # section chain (it includes waypoints on the NCT west and south
    # of the chapter's depicted stretch). A waypoint near the chain
    # (<= SNAP_LIMIT_M) takes the chain's chainage/NCT mile/section;
    # a farther one is OFF-CHAIN: it keeps its true position and its
    # snap distance, but chainage, NCT mile and section stay null —
    # assigning it the chain end's values would fabricate a position
    # along the chapter's trail.
    parking_coords = []
    off_chain = 0
    superseded = {}
    for cf in chapter_places:
        cp = cf["properties"]
        if cp.get("supersedes"):
            superseded[cp["supersedes"]] = cp.get("id")
    superseded_dropped = 0
    for f in ncta:
        p = f["properties"]
        coord = f["geometry"]["coordinates"]
        key = "ncta-points:%s@%.6f,%.6f" % (
            clean(p.get("name")) or "", coord[0], coord[1])
        if key in superseded:
            superseded_dropped += 1
            continue  # the chapter entry below replaces this point
        kind = clean(p.get("type")) or "POI"
        if kind == "Parking":
            parking_coords.append(coord)
        piece, ch, snap = project(pieces, coord)
        name = clean(p.get("name")) or kind
        extra = {}
        desc = scrub_contacts(clean(p.get("description")), stats)
        if desc:
            extra["description"] = desc
        if snap > SNAP_LIMIT_M:
            off_chain += 1
            extra["off_chain"] = True
            add(name, kind, "ncta-points", coord, None, None, None,
                snap, extra)
        else:
            add(name, kind, "ncta-points", coord, ch,
                nct_from_chainage(pieces, ch), piece.name, snap, extra)

    # ---- chapter places ----
    # The chapter's own records, projected exactly like the NCTA
    # waypoints (same SNAP_LIMIT_M off-chain rule). Source is
    # "chapter"; the record's own provenance rides in place_source.
    chapter_off_chain = 0
    for f in chapter_places:
        p = f["properties"]
        coord = f["geometry"]["coordinates"]
        kind = clean(p.get("kind")) or "POI"
        name = clean(p.get("name")) or kind
        extra = {
            "place_id": p.get("id"),
            "status": clean(p.get("status")),
            "capacity": clean(p.get("capacity")),
            "water_note": clean(p.get("water_note")),
            "place_source": clean(p.get("source")),
            "photo_drive_id": p.get("photo_drive_id"),
        }
        desc = clean(p.get("description"))
        if desc:
            extra["description"] = desc
        piece, ch, snap = project(pieces, coord)
        if snap > SNAP_LIMIT_M:
            chapter_off_chain += 1
            extra["off_chain"] = True
            add(name, kind, "chapter", coord, None, None, None,
                snap, extra)
        else:
            add(name, kind, "chapter", coord, ch,
                nct_from_chainage(pieces, ch), piece.name, snap, extra)

    # ---- access crossings (deduped against NCTA parking) ----
    deduped = 0
    for f in access_pts:
        p = f["properties"]
        coord = f["geometry"]["coordinates"]
        if any(dist_km(coord, pc) * 1000.0 <= DEDUPE_PARKING_M
               for pc in parking_coords):
            deduped += 1
            continue
        kind = "Road crossing" if p.get("kind") == "road" \
            else "Trail crossing"
        section = p.get("for_name") if p.get("for_type") == "segment" \
            else "GAP-W"
        piece, ch, snap = project(pieces, coord)
        add(clean(p.get("label")) or kind, kind, "access-points", coord,
            ch, nct_from_chainage(pieces, ch), section, snap)

    entries.sort(key=lambda e: (e["properties"]["chainage_mi"]
                                if e["properties"]["chainage_mi"]
                                is not None else 1e9,
                                e["properties"]["kind"],
                                e["properties"]["name"]))
    dst = os.path.join(ROOT, "site/data/gazetteer.geojson")
    with open(dst, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": entries},
                  fh, separators=(",", ":"))

    # ---- report ----
    from collections import Counter
    by_kind = Counter(e["properties"]["kind"] for e in entries)
    by_source = Counter(e["properties"]["source"] for e in entries)
    with_nct = sum(1 for e in entries
                   if e["properties"]["nct_mile"] is not None)
    print(f"gazetteer: {len(entries)} entries -> site/data/gazetteer.geojson "
          f"({os.path.getsize(dst)/1e3:.0f} KB)")
    print("by kind:", dict(by_kind))
    print("by source:", dict(by_source))
    print(f"with NCT mile: {with_nct}/{len(entries)}")
    print(f"access crossings dropped (within {DEDUPE_PARKING_M:.0f} m of "
          f"an NCTA parking point): {deduped}")
    print(f"NCTA waypoints off-chain (> {SNAP_LIMIT_M:.0f} m snap; "
          f"chainage/NCT/section null): {off_chain}")
    print(f"NCTA waypoints superseded by chapter places (dropped; "
          f"the chapter entry replaces each): {superseded_dropped}")
    print(f"chapter places indexed: {len(chapter_places)} "
          f"(off-chain: {chapter_off_chain})")
    print(f"tracker texts with an unresolvable first-name residue "
          f"(left as recorded): {stats.get('name_residues', 0)}")
    print(f"contact patterns stripped from tracker text: "
          f"{stats['contact_strips']}")
    print(f"'@' shorthand rewritten in comments: "
          f"{stats['at_signs_rewritten']}")
    print(f"sawyer-only placeholders added: "
          f"{next_num[0] - sawyer_only_start} "
          f"(numbering now reaches Test adopter {next_num[0] - 1})")
    print("comments review:")
    for e in entries:
        p = e["properties"]
        if p["kind"] != "Section":
            continue
        if p.get("comments"):
            print(f"  CARRIED {p['name']}: {p['comments']}")
        elif p.get("comments_dropped"):
            print(f"  DROPPED {p['name']} (unmatched personal reference)")


if __name__ == "__main__":
    sys.exit(main())

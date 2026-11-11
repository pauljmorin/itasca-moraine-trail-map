#!/usr/bin/env python3
"""Initials for adopter/sawyer display on the public trail map.

Paul's ruling, 2026-11-11: the public site shows adopter and sawyer
INITIALS instead of the "Test adopter N" placeholders used before.
Initials are derived from the tracker person string: first letters
of first + last name; a first-name-only person gets one letter; a
parenthetical nickname is ignored (Ron (Skip) Duchesneau -> RD).
"X and Y Surname" cells split into two people first (the tracker's
join does not split "and").

Collision decided by Paul (tap, 2026-11-11): Brent Johnson -> "BJ",
Bruce Johnson -> "BrJ". All other collisions stand as derived:
Chris vs Carol -> "C"; Laurie vs Larry -> "L".

Standard library only. Imported by scripts/build_site_data.py and
scripts/build_gazetteer.py; both must use these helpers so the two
builds can never disagree on a person's initials.
"""

import re

# Paul's decided disambiguation (2026-11-11): the only collision
# broken apart. Every other collision keeps the derived initials.
_OVERRIDES = {
    "Bruce Johnson": "BrJ",
}

_NON_PERSON = re.compile(r"^contact\b", re.IGNORECASE)

_AND_CELL = re.compile(
    r"^([A-Za-z]+) and ([A-Za-z]+) ([A-Za-z][A-Za-z'\u2019\-]*)$")


def split_and_people(name):
    """Split a tracker cell like "Patty and Tom O'Reilly" into two
    person strings; anything else passes through unchanged."""
    m = _AND_CELL.match((name or "").strip())
    if not m:
        return [name]
    return ["%s %s" % (m.group(1), m.group(3)),
            "%s %s" % (m.group(2), m.group(3))]


def expand_people(names):
    """Flat list of person strings, with "X and Y Surname" cells split."""
    out = []
    for n in names or []:
        out.extend(split_and_people(n))
    return out


def is_person_chunk(chunk):
    """False for instruction text that is not a person
    ("Contact Janita" is a direction to phone someone, not a name)."""
    return bool(chunk and chunk.strip()) and \
        not _NON_PERSON.match(chunk.strip())


def initials_for_person(name):
    """Initials for one person string: first letters of first + last
    name (parenthetical nicknames ignored); one letter for a
    first-name-only person."""
    if name in _OVERRIDES:
        return _OVERRIDES[name]
    bare = re.sub(r"\(.*?\)", "", name or "").strip()
    parts = bare.split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def initials_for_people(names):
    """Initials list for a list of person strings, in order."""
    return [initials_for_person(n) for n in expand_people(names)]

#!/usr/bin/env python3
"""Add a `timing` property (past | planned) to every feature of
site/data/timber-sales-minnesota.geojson (Paul, Nov 16, 2026).

The split is PAST vs PLANNED, across every program — not exams-vs-sales:

- PAST: sold/completed sales — county-sale / usfs-edw-sale features
  with a sale/award year in the past (a recorded sale year up to now,
  2026 included) or a closed/sold status.
- PLANNED: everything not yet cut — both DNR stand-exam programs
  (an exam is not a sale; DNR's caveat is that not every examined
  stand becomes a sale) AND upcoming county sales/appraisals.

Rule, in order:
  1. program dnr-stand-exam-10yr / dnr-stand-exam-annual -> planned.
  2. Hubbard status == "upcoming" -> planned; "sold" -> past
     (the county's own status is authoritative).
  3. Becker closed == "Yes" -> past; "No" -> planned;
     closed null falls through to the year rule.
  4. Otherwise (Cass, Becker fall-through, EDW): a recorded year
     <= 2026 -> past (the year IS the sale year); year null ->
     planned (current listing / undated sale area — cannot confirm
     a cut happened). Year-null features decided by this fallback
     are counted as AMBIGUOUS and reported.

Expected counts (2026-11-16): planned 1,190 (exams 1,166 + Cass
year-null 8 + Becker closed-No 1 + Becker closed-null/year-null 14
+ EDW MARBLES year-null 1); past 361. Ambiguous: 23 (Cass 8,
Becker 14, EDW 1) — all placed in planned, per the rule above.

Control numbers (must not change): 1,551 features; program counts
county-sale 340 / usfs-edw-sale 45 / dnr-stand-exam-10yr 1,077 /
dnr-stand-exam-annual 89; total acres 91,454.3.
"""

import json
from collections import Counter

PATH = "site/data/timber-sales-minnesota.geojson"

EXAMS = ("dnr-stand-exam-10yr", "dnr-stand-exam-annual")


def decide(p):
    """Return (timing, ambiguous_bool)."""
    if p.get("program") in EXAMS:
        return "planned", False
    # Hubbard: the county's own sold/upcoming status is authoritative.
    status = p.get("status")
    if status == "upcoming":
        return "planned", False
    if status == "sold":
        return "past", False
    # Becker: Closed is the past/future signal where filled.
    closed = p.get("closed")
    if closed == "Yes":
        return "past", False
    if closed == "No":
        return "planned", False
    # Otherwise: a recorded sale/award year up to now means sold.
    year = p.get("year")
    if isinstance(year, (int, float)) and year <= 2026:
        return "past", False
    # No year and no status signal: cannot confirm a cut happened.
    # Current listing / appraisal / undated sale area -> planned,
    # and flagged ambiguous for the report.
    return "planned", True


def main():
    with open(PATH) as fh:
        data = json.load(fh)
    feats = data["features"]

    # Control numbers BEFORE the patch.
    before_programs = Counter(f["properties"].get("program") for f in feats)
    before_regions = Counter(f["properties"].get("region") for f in feats)
    before_acres = round(
        sum(f["properties"].get("acres") or 0 for f in feats), 1)

    timing = Counter()
    ambiguous = Counter()
    cross = Counter()
    for f in feats:
        p = f["properties"]
        t, amb = decide(p)
        p["timing"] = t
        timing[t] += 1
        cross[(p.get("program"), t)] += 1
        if amb:
            ambiguous[p.get("program")] += 1

    with open(PATH, "w") as fh:
        json.dump(data, fh)

    # Control numbers AFTER the patch (re-read from disk).
    with open(PATH) as fh:
        check = json.load(fh)
    cfeats = check["features"]
    after_programs = Counter(f["properties"].get("program") for f in cfeats)
    after_regions = Counter(f["properties"].get("region") for f in cfeats)
    after_acres = round(
        sum(f["properties"].get("acres") or 0 for f in cfeats), 1)
    assert len(cfeats) == 1551, len(cfeats)
    assert after_programs == before_programs, (before_programs, after_programs)
    assert after_regions == before_regions, (before_regions, after_regions)
    assert after_acres == before_acres == 91454.3, (before_acres, after_acres)
    assert timing["planned"] == 1190, timing
    assert timing["past"] == 361, timing

    print("features:", len(cfeats))
    print("timing:", dict(timing))
    print("program x timing:", dict(cross))
    print("ambiguous (fallback -> planned):", dict(ambiguous),
          "total:", sum(ambiguous.values()))
    print("control OK: programs", dict(after_programs),
          "| regions", dict(after_regions), "| acres", after_acres)


if __name__ == "__main__":
    main()

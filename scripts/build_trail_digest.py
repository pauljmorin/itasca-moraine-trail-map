#!/usr/bin/env python3
"""Build the "Ask the trail" digest: site/data/trail-digest.json.

A compact, checked-in summary of the chapter map's own data, generated
from the repo's GeoJSON flat files plus a small set of verified figures
from the build-out research docs (each labelled with its source). The
itm-save Worker's /ask endpoint sends this digest — and nothing else —
to the model, so every answer the map gives is grounded in the map's
own data. Re-run after any data refresh:

  python3 scripts/build_trail_digest.py

Fences carried into the digest by construction:
  - Adopter display is INITIALS ONLY (adopter_display in stretches).
  - Parcels carry owner names (published county records) and NO
    taxpayer fields — the digest never adds any.
  - No photo classification or condition judgment: the digest reports
    recorded condition values only.
  - No invented numbers: figures not computed from the files carry
    an explicit "source" naming the research doc they came from.
"""
import json
import os
import re
from collections import Counter
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "site", "data")
OUT = os.path.join(DATA, "trail-digest.json")

TYPE_NAMES = {
    "BN": "Bench", "BO": "Bollard", "BR": "Bridge", "BW": "Boardwalk",
    "CP": "Carsonite post", "CS": "Campsite", "KI": "Kiosk",
    "LT": "Latrine", "PK": "Parking area", "PO": "Post",
    "RG": "Register", "SG": "Sign", "SH": "Shelter",
    "UN": "Unclassified", "WT": "Water source",
}

# Public/private owner patterns, same family as the gap-parcels design
# (docs/gap-parcels-design.md §4): name-anchored public patterns, then
# land-class signals. Economic-development authorities and cemetery
# associations classify private under this rule (known edge cases,
# docs/gap-parcels-test-note.md) — the digest says so, it does not
# hide it.
PUBLIC_OWNER_RES = [
    re.compile(p, re.I) for p in [
        r"^state of minn", r"^state of mn\b", r"^united states",
        r"^u\.s\.", r"^department of natural resources",
        r" county\b", r"^city of ", r"^town of ",
        r"^township of ", r" school dist", r"independent school",
        r"^federal ", r" national forest",
    ]
]
PUBLIC_LANDCLASS_RES = [
    re.compile(p, re.I) for p in [
        r"tax forfeit", r"\bstate\b", r"federal", r"county admin",
        r"school trust", r"concon", r"pilt",
    ]
]


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def pub_priv(owner, land_class):
    owner = (owner or "").strip()
    lc = (land_class or "").strip()
    for rx in PUBLIC_OWNER_RES:
        if rx.search(owner):
            return "public"
    for rx in PUBLIC_LANDCLASS_RES:
        if rx.search(lc):
            return "public"
    return "private"


def main():
    stretches = load("stretches.geojson")["features"]
    assets = load("assets.geojson")["features"]
    gaps = load("gaps.geojson")["features"]
    parcels = load("parcels.geojson")["features"]
    trail_mn = load("trail-minnesota.geojson")["features"]
    easements = load("easements.geojson")["features"]

    sections = []
    adopted_mi = 0.0
    for f in stretches:
        p = f["properties"]
        mi = round(float(p.get("length_mi") or 0), 2)
        if p.get("has_adopter"):
            adopted_mi += mi
        sections.append({
            "name": p.get("name"),
            "tracker_section": p.get("tracker_section"),
            "length_mi": mi,
            "has_adopter": bool(p.get("has_adopter")),
            # INITIALS ONLY — never expand to names.
            "adopter_initials": p.get("adopter_display") or [],
        })
    sections.sort(key=lambda s: (s["tracker_section"] or s["name"] or ""))

    gap_list = [{
        "gap_id": f["properties"].get("gap_id"),
        "name": f["properties"].get("name"),
        "length_mi": round(float(f["properties"].get("length_mi") or 0), 2),
        "classification": f["properties"].get("classification"),
        "land_context": f["properties"].get("land_context"),
    } for f in gaps]
    gap_mi = round(sum(g["length_mi"] for g in gap_list), 2)

    type_counts = Counter()
    cond_counts = Counter()
    asset_list = []
    for f in assets:
        p = f["properties"]
        t = (p.get("type") or "UN").upper()
        if t == "UNCLASSIFIED":
            t = "UN"
        c = p.get("condition")
        type_counts[t] += 1
        cond_counts[c if c else "ungraded"] += 1
        asset_list.append({
            "serial": p.get("serial"),
            "type": t,
            "type_name": TYPE_NAMES.get(t, t),
            # Recorded value only; null means unclassified, not "unknown".
            "condition": c,
        })
    asset_list.sort(key=lambda a: (a["serial"] is None, a["serial"] or ""))

    parcel_pub = parcel_priv = 0
    parcel_by_county = Counter()
    parcel_by_corridor = Counter()
    owner_acres = Counter()
    parcels_without_owner = 0
    for f in parcels:
        p = f["properties"]
        if not p.get("owner"):
            parcels_without_owner += 1
        if pub_priv(p.get("owner"), p.get("land_class")) == "public":
            parcel_pub += 1
        else:
            parcel_priv += 1
        parcel_by_county[p.get("county") or "unknown"] += 1
        parcel_by_corridor[str(p.get("corridor"))] += 1
        if p.get("owner"):
            owner_acres[p.get("owner")] += float(p.get("acres") or 0)
    top_owners = [
        {"owner": o, "acres": round(a, 1)}
        for o, a in owner_acres.most_common(10)
    ]

    timber = {}
    for fname, label in [
        ("logging-becker-timber-sales.geojson", "Becker County"),
        ("logging-cass-timber-sales.geojson", "Cass County"),
        ("logging-hubbard-timber-sales.geojson", "Hubbard County"),
        ("logging-clearwater-timber-sales.geojson", "Clearwater County"),
        ("logging-edw-timber-sale.geojson", "Chippewa National Forest"),
    ]:
        feats = load(fname)["features"]
        by_year = Counter(
            str(f["properties"].get("year"))
            for f in feats if f["properties"].get("year"))
        timber[label] = {
            "sales_total": len(feats),
            "by_year": dict(sorted(by_year.items())),
            "acres_total": round(sum(
                float(f["properties"].get("acres") or 0)
                for f in feats), 1),
        }

    digest = {
        "meta": {
            "generated": date.today().isoformat(),
            "generator": "scripts/build_trail_digest.py",
            "about": "Compact summary of the Itasca Moraine chapter map's "
                     "own data, for the Ask the trail Q&A. The model "
                     "answers ONLY from this digest.",
            "sources": [
                "site/data/stretches.geojson",
                "site/data/assets.geojson",
                "site/data/gaps.geojson",
                "site/data/parcels.geojson",
                "site/data/trail.geojson",
                "site/data/trail-minnesota.geojson",
                "site/data/easements.geojson",
                "site/data/logging-*.geojson",
                "docs/gap-grand-rapids-ely-research.md",
                "docs/gap-detroit-lakes-sd-research.md",
                "docs/gap-economics-safety-research.md",
                "docs/gap-atv-competition-research.md",
                "docs/gap-ncta-track-record-research.md",
                "docs/buildout-viewer-notes.md",
            ],
        },
        "trail": {
            "chapter": "Itasca Moraine chapter, North Country Trail",
            "depicted_mi": round(adopted_mi + gap_mi, 2),
            "adopted_mi": round(adopted_mi, 2),
            "unadopted_mi": gap_mi,
            "sections_count": len(sections),
            "sections": sections,
            "gaps": gap_list,
            "gap_note": "The only unadopted stretch is GAP-W, 2.92 mi at "
                        "the west end, inside Itasca State Park, roadless. "
                        "It needs an adopter.",
        },
        "assets": {
            "total": len(assets),
            "by_type": [
                {"code": c, "name": TYPE_NAMES.get(c, c), "count": n}
                for c, n in sorted(type_counts.items(),
                                   key=lambda kv: -kv[1])
            ],
            "by_condition_recorded": dict(sorted(cond_counts.items())),
            "unclassified_count": cond_counts.get("ungraded", 0),
            "list": asset_list,
        },
        "parcels": {
            "total": len(parcels),
            "crossed_by_trail": parcel_by_corridor.get("crossed", 0),
            "adjoining_trail": parcel_by_corridor.get("adjoining", 0),
            "by_county": dict(sorted(parcel_by_county.items())),
            "public_private_split": {
                "public": parcel_pub, "private": parcel_priv,
                "rule": "Owner-name patterns (State/County/City/Town/DNR/"
                        "USA/school) plus land-class signals (tax-forfeit/"
                        "PILT/State/Federal/County Admin). Same family as "
                        "docs/gap-parcels-design.md. Economic-development "
                        "authorities and cemetery associations classify "
                        "private under this rule.",
            },
            "top_owners_by_acres": top_owners,
            "parcels_without_owner_name": parcels_without_owner,
            "note": "Owner names are published county records. No "
                    "taxpayer fields exist in this data and none are "
                    "included here. 119 parcels carry no owner name in "
                    "the file and are excluded from the top-owners list.",
        },
        "timber": {
            "note": "Timber sales are listed by year as published. "
                    "'Active' is not a recorded status — do not present "
                    "a year as active or closed unless the file says so.",
            "by_manager": timber,
        },
        "land": {
            "conservation_easements": {
                "count": len(easements),
                "acres_total": round(sum(
                    float(f["properties"].get("acres") or 0)
                    for f in easements), 1),
                "source": "site/data/easements.geojson (BWSR RIM)",
            },
            "forest_health_2025_detections": len(
                load("forest-health-2025.geojson")["features"]),
            "invasive_sightings": len(
                load("invasive-sightings.geojson")["features"]),
            "chippewa_plan_areas": len(
                load("chippewa-plan-areas.geojson")["features"]),
            "canopy": "Six discrete 5 m height bands (0-5 to 25+ m); "
                      "hillshade removed Nov 12, 2026; height lines "
                      "removed Nov 13, 2026.",
        },
        "minnesota": {
            "nct_features_statewide": len(trail_mn),
            "nct_miles_statewide": 566.12,
            "nct_miles_source": "NCTA nct_public ArcGIS service "
                                "(official line, state == MN)",
            "map_sheets": "MN-001 to MN-104 (full NCTA series)",
            "street_view_markers": len(load("streetview.geojson")["features"]),
            "mile_markers": len(load("milemarkers.geojson")["features"]),
            "chapter_places": len(load("chapter-places.geojson")["features"]),
        },
        "buildout_verified": {
            "source": "docs/buildout-viewer-notes.md, "
                      "docs/gap-grand-rapids-ely-research.md, "
                      "docs/gap-detroit-lakes-sd-research.md",
            "arrowhead_gap_mi": 182.62,
            "arrowhead_foot_tread_mi": 1.44,
            "western_gap_mi": 106.1,
            "western_foot_tread_mi": 5.98,
            "proposed_arrowhead_offroad_mi": 101.45,
            "proposed_western_offroad_mi": 104.49,
            "note": "Gap mileages are the assessment's headline figures; "
                    "the viewer's drawn files total 152.80 mi (Arrowhead) "
                    "and 104.86 mi (western) — see buildout-viewer-notes.md "
                    "for the reconciliation.",
        },
        "economics_safety_verified": {
            "source": "docs/gap-economics-safety-research.md",
            "mn_state_trails_visitors_2024": "2.3M",
            "mn_state_trails_output_per_year": "$102.5M",
            "mn_state_trails_jobs": "626+",
            "output_per_visitor": "~$44.60 (arithmetic)",
            "mesabi_trail_users_2025": "~285,000 (count only; no Mesabi "
                                       "spending study exists)",
            "separated_walkway_crash_reduction": "up to 88% (FHWA, "
                "site-likelihood, not all pedestrian crashes)",
            "paved_shoulder_crash_reduction": "up to 71% (FHWA)",
            "value_of_statistical_life_2025": "$14.2M (US DOT)",
        },
        "motorized_verified": {
            "source": "docs/gap-atv-competition-research.md",
            "atv_miles_corridor_core": "~1,083 (arithmetic sum of "
                "published system mileages; systems share tread)",
            "prospector_loop_mi": "167 (DNR); club says 216+, SEH says "
                                  "250 — unsettled",
            "snowmobile_named_systems_mi": "598",
            "highway_2_rule": "Minn. Stat. 84.777: unsigned forest access "
                "routes north of US Highway 2 are open to OHV riding "
                "unless posted closed. Building a NEW trail still needs "
                "DNR designation and environmental review.",
            "hf1012_sf1245": "Would impose signed-trails-only statewide "
                "and repeal the north-of-Highway-2 carve-out. Not enacted.",
        },
        "ncta_track_record_verified": {
            "source": "docs/gap-ncta-track-record-research.md",
            "new_offroad_tread_built_nationally_2016_2025_mi": 455.15,
            "new_offroad_tread_minnesota_2016_2026_mi": "~16 at most "
                "(6 mi Arrowhead 2024 + 9.8 mi Fergus Falls urban loop 2016)",
            "western_gap_new_tread_mi": 0,
            "trail_protection_director": "Paul Gagnon, Director of Trail "
                "Protection (since at least 2022)",
            "planning_director": "None on staff; planning sits with the "
                "Director of Trail Operations and one regional coordinator "
                "for ND/MN/WI",
            "canal_park_claim": "NOT FOUND in the annual reports checked — "
                "do not assert NCTA claimed the Canal Park redevelopment. "
                "Checkable wording: NCTA counts Minnesota miles through "
                "Canal Park (Superior Hiking Trail) that it never built.",
        },
        "not_covered": [
            "Per-road posted speeds, traffic counts (AADT), and shoulder "
            "widths for the gap road walks (MnDOT live check in progress, "
            "Nov 13, 2026).",
            "Hiker/visitor counts for the chapter trail itself (no trail "
            "counters in the data; the Mesabi Trail's ~285,000 users/yr "
            "and the statewide 2.3M state-trail visitors are analogues, "
            "not chapter counts).",
            "Future timber sales or planned clear-cuts (all timber layers "
            "are past sales; DNR 4trees / Chippewa NF SOPA not yet wired).",
            "Per-parcel taxpayer information (excluded by design).",
            "Adopter names, phone numbers, or email addresses (initials "
            "only, by design).",
            "Anything dated after this digest was generated.",
        ],
    }

    with open(OUT, "w") as f:
        json.dump(digest, f, indent=1)
        f.write("\n")
    print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()

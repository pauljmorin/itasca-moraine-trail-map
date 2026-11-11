# Staged app.js patch — asset serial in the popup title

**APPLIED Nov 11, 2026** (commit below) — `site/app.js` was freed when
the sheets agent (4939f96a) completed, the patch was applied verbatim,
and the popup was verified by running the real `assetPopup`/`esc`/
`kvTable` code in Node: "ITM-BN-014 — Bench" with a Section row, and
"Unclassified" with no Section row when unassigned. This file is kept
as the record of the change.

Design: `docs/asset-serial-numbers-2026-11-11.md` §5/§7. The popup
title becomes serial + type ("ITM-BN-014 — Bench"); unassigned pins
keep showing the type as today. No marker change. The Section row
uses the `section` field the pipeline now stamps (the "on West-9"
context); it is omitted when the pin is off-chain (`section` null).

## Location

`site/app.js`, `assetPopup`, lines 979–986 (as of 2026-11-11,
commit cbb7dd7). `esc` (line 745) and `kvTable` (line 752)
already exist. The capitalize idiom matches line 917
(`p.status.charAt(0).toUpperCase() + p.status.slice(1)`).

## Current

```js
function assetPopup(f) {
  var p = f.properties || {};
  return "<h3>" + (esc(p.type) || "Asset") + "</h3>" + kvTable([
    ["Condition", p.condition],
    ["Photographed", p.datetime],
  ]);
}
```

## Patched

```js
function assetPopup(f) {
  var p = f.properties || {};
  var typeName = esc(p.type) || "Asset";
  typeName = typeName.charAt(0).toUpperCase() + typeName.slice(1);
  var title = p.serial ? esc(p.serial) + " — " + typeName : typeName;
  return "<h3>" + title + "</h3>" + kvTable([
    ["Condition", p.condition],
    ["Photographed", p.datetime],
    ["Section", p.section],
  ]);
}
```

Notes:

- `kvTable` already skips null values (verified: the existing
  Condition row renders nothing when `condition` is null), so the
  Section row is simply absent on off-chain pins. If that
  assumption ever proves wrong, guard it with
  `p.section ? ["Section", p.section] : null` and filter nulls.
- No change to `assetMarker` (lines 994+) — the condition-colour
  ring is unchanged.
- Optional later, not in this patch: make serials searchable
  (gazetteer `search_text` gains serials) — deferred until the
  first real batch lands, per the design note.

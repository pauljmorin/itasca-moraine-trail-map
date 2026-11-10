/* Itasca Moraine Chapter — Trail Map (working draft), v1.
 *
 * Single-page Leaflet map. Plain script, no build step, no API keys.
 * Data: simplified site copies under data/ (built by
 * scripts/build_site_data.py from the working data in ../data/).
 *
 * PRIVACY: the parcel layer shows parcel ID, county, land class,
 * acres, and the OWNER name + mailing address exactly as published
 * in the county parcel records — public record, shown per the
 * chapter's 2026-11-10 ruling (see scripts/build_site_data.py).
 * Maintainer contact fields in the access source data are stripped
 * and never displayed. Adopter names follow the opposite rule: the
 * site copies of the stretches carry PLACEHOLDER names only
 * ("Test adopter 1", "Test adopter 2", ...) assigned by the build
 * script; the real adopter names exist only in the working data
 * and are never copied into any site file.
 *
 * STRUCTURE: layers load lazily the first time their toggle is
 * switched on; each is just an entry in LAYERS below.
 */
"use strict";

/* ------------------------------------------------------------- map */

var map = L.map("map", { center: [47.02, -94.95], zoom: 10 });

var osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors",
}).addTo(map);

var topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  maxZoom: 17,
  attribution: "Map data: © OpenStreetMap contributors, SRTM | " +
    "map style: © OpenTopoMap (CC-BY-SA)",
});

/* Shaded relief + aerial base layers (v2). Endpoints verified live
   2026-11-10 (sample tiles / WMS GetMap fetched — see SOURCES.md).
   The MnGeo hillshade comes from the Minnesota Geospatial Image
   Service (WMS, Web Mercator endpoint): "hillshd" is the statewide
   hillshade derived from 1 m LiDAR.
   v3 (Nov 10, Paul's calls): the USGS shaded-relief base was cut
   ("shit data" next to the 1 m LiDAR hillshade), the MnGeo spring
   aerial (nw14) was cut (shows nothing useful over the chapter),
   and the USGS Topo base was added — The National Map's topo,
   built from the 1:24,000 quadrangle series. */
var MN_WMS = "https://imageserver.gisdata.mn.gov/cgi-bin/wmswm?";
var mnHillshade = L.tileLayer.wms(MN_WMS, {
  layers: "hillshd", format: "image/jpeg", transparent: false,
  version: "1.1.1",
  attribution: "Shaded relief (LiDAR hillshade): MnGeo / Minnesota DNR",
});
var usgsTopo = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSTopo/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16,
    attribution: "Topo: USGS, The National Map",
  });
var usgsImagery = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16,
    attribution: "Aerial imagery: USGS, The National Map (NAIP)",
  });
var esriImagery = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/" +
    "World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 18,
    attribution: "Aerial imagery: Esri, Maxar, Earthstar Geographics",
  });

L.control.layers(
  {
    "OpenStreetMap": osm,
    "Topo (OpenTopoMap)": topo,
    "Topo (USGS 1:24k)": usgsTopo,
    "Shaded relief (MN LiDAR)": mnHillshade,
    "Aerial — USGS (NAIP)": usgsImagery,
    "Aerial — Esri World Imagery": esriImagery,
  }, null,
  { position: "topright" }
).addTo(map);
L.control.scale({ imperial: true, metric: true }).addTo(map);

/* Heavy vector layers draw on CANVAS, not SVG: parcels (1,038
   features), roads (5,902) and access lines (3,670) as thousands of
   DOM paths made layer toggles visibly slow, while a canvas redraws
   in a single pass and popups/hit-testing still work. ALL of them
   share ONE canvas renderer in the default overlay pane: a single
   draw list is what lets bringToFront keep the stacking order
   (parcels at the back, lines on top — see assertDrawOrder). A
   canvas renderer in a CUSTOM pane was tried first and rejected:
   in Leaflet 1.9.4 its paths render but stop receiving clicks
   (verified in the proof harness — popup only via SVG/default
   canvas), so no custom panes here. The small point layers keep
   the default SVG renderer; assertDrawOrder also keeps the SVG
   element above the canvas element in the shared pane. */
var heavyCanvas = L.canvas();
function canvasFor() { return heavyCanvas; }

/* ------------------------------------------------------------ style */

var CHAPTER_COLORS = { ITM: "#1a9850", LLC: "#762a83" };
var CHAPTER_NAMES = {
  ITM: "Itasca Moraine Chapter",
  LLC: "Laurentian Lakes Chapter",
};

function trailStyle(f) {
  var p = f.properties;
  var onRoad = p.trail_stat === "NCT (on-road)" || p.trail_type === "Public Road";
  return {
    color: CHAPTER_COLORS[p.chapter] || "#444444",
    weight: onRoad ? 2.5 : 4,
    opacity: 0.9,
    dashArray: onRoad ? "6 6" : null,
  };
}

/* Access lines drawn THIN (Paul, Nov 10, 2026): they're context for
   reaching the trail, not the subject — hairlines that sit quietly
   under the trail line. */
var ACCESS_STYLES = {
  state_forest_road:     { color: "#8c510a", weight: 1,   label: "State forest road" },
  state_park_trail_or_road: { color: "#35978f", weight: 1, label: "State park trail / road" },
  ohv_trail:             { color: "#d7301f", weight: 1,   label: "OHV / ATV-UTV trail" },
  state_trail:           { color: "#2c7fb8", weight: 1.25, label: "State trail" },
  snowmobile_trail:      { color: "#8856a7", weight: 0.75, dashArray: "2 5", label: "Snowmobile trail" },
  hunter_walking_trail:  { color: "#31a354", weight: 0.75, dashArray: "8 4", label: "Hunter walking trail" },
};

function accessStyle(f) {
  var s = ACCESS_STYLES[f.properties.source_type] ||
    { color: "#666666", weight: 1 };
  return { color: s.color, weight: s.weight, opacity: 0.75,
           dashArray: s.dashArray || null };
}

function parcelStyle(f) {
  var crossed = f.properties.corridor === "crossed";
  return {
    color: crossed ? "#b35806" : "#a89a5b",
    weight: crossed ? 1.2 : 0.6,
    fillColor: crossed ? "#fdbb84" : "#e7e1c3",
    fillOpacity: crossed ? 0.45 : 0.25,
  };
}

/* Adopted stretches ride on top of the official line in amber, wide
   enough to read as a highlight of the green beneath. */
var STRETCH_STYLE = { color: "#e08214", weight: 6, opacity: 0.8 };

/* The unadopted gap is the recruiting layer — it must be the most
   visible line on the map: a pale red casing under a bold dashed
   red core (the closest plain Leaflet gets to a hatched line). */
var GAP_CASING_STYLE = { color: "#b2182b", weight: 11, opacity: 0.3 };
var GAP_CORE_STYLE = {
  color: "#d7301f", weight: 5, opacity: 1, dashArray: "12 7",
};

/* ------------------------------------------------------------ popups */

function esc(v) {
  if (v === null || v === undefined || v === "") return null;
  return String(v).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

function kvTable(rows) {
  var html = "<table>";
  rows.forEach(function (r) {
    var v = esc(r[1]);
    if (v !== null) html += "<tr><td class='k'>" + r[0] + "</td><td>" + v + "</td></tr>";
  });
  return html + "</table>";
}

function trailPopup(f) {
  var p = f.properties;
  var title = esc(p.seg_name) || "North Country Trail";
  var kind = p.trail_stat === "NCT (on-road)" ? "On-road section" : "Off-road trail";
  return "<h3>" + title + "</h3>" + kvTable([
    ["Chapter", CHAPTER_NAMES[p.chapter] || p.chapter],
    ["Type", kind + (p.trail_type ? " (" + p.trail_type + ")" : "")],
    ["Certification", p.cert_stat],
    ["Length", p.len_miles ? p.len_miles + " mi" : null],
    ["Ownership", p.ownership],
    ["Managing authority", p.mng_auth],
    ["Surface", p.trail_surf],
    ["Closure", p.closure],
  ]);
}

function parcelPopup(f) {
  var p = f.properties;
  return "<h3>Parcel " + (esc(p.parcel_id) || "—") + "</h3>" + kvTable([
    ["County", p.county],
    ["Land class", p.land_class],
    ["Acres", p.acres],
    ["Trail corridor", p.corridor === "crossed"
      ? "Trail crosses this parcel" : "Adjoins a crossed parcel"],
    ["Owner", p.owner],
    ["Owner address", p.owner_address],
  ]) + "<p><em>Owner as published in the county parcel records " +
    "(public record).</em></p>";
}

function accessPopup(f) {
  var p = f.properties;
  var s = ACCESS_STYLES[p.source_type];
  return "<h3>" + (esc(p.name) || (s ? s.label : "Access line")) + "</h3>" +
    kvTable([
      ["Kind", s ? s.label : p.source_type],
      ["Class", p.road_class],
      ["Length", p.miles ? p.miles + " mi" : null],
      ["Source", p.dataset],
    ]);
}

function roadPopup(f) {
  var n = esc(f.properties.name);
  return n ? "<h3>" + n + "</h3>" : null;
}

function assetPopup(f) {
  var p = f.properties || {};
  return "<h3>" + (esc(p.type) || "Asset") + "</h3>" + kvTable([
    ["Condition", p.condition],
    ["Photographed", p.datetime],
    ["Photographer", p.photographer],
  ]);
}

/* Segment popups show section identity, lengths, access, and the
   PLACEHOLDER adopter names from the site copy ("Test adopter N")
   — real adopter names are never in the site data (see the header
   privacy note). */
/* Hover card for a section (Paul, Nov 10, 2026: "when I mouse over
   the segment name can you bring up information from the
   spreadsheet?"). Content = the section's gazetteer record (the
   tracker/spreadsheet fields, public-safe form), built by
   gazPopupHtml once the index is loaded; before that, the stretch's
   own popup content stands in. Interactive tooltips can't be
   hovered themselves, so the card follows the cursor (sticky) and
   dismisses on mouse-out; a click still opens the section's popup. */
var sectionHoverTip = null;
function sectionHoverHtml(feature, stretchProps) {
  if (gazFeatures) {
    var name = stretchProps && stretchProps.name;
    for (var i = 0; i < gazFeatures.length; i++) {
      var f = gazFeatures[i];
      if (f.properties.kind === "Section" && f.properties.name === name) {
        return gazPopupHtml(f);
      }
    }
  }
  return stretchPopup(feature);
}

/* Where a section's name label sits (Paul, Nov 10, 2026): above the
   line works on east–west segments, but on a north–south segment
   "above" parks the name on the tread's end — so vertical segments
   get the name BESIDE the line instead. Judged from the segment
   direction at the section's length-centroid (where Leaflet
   anchors the tooltip): |dy| > |dx| → beside (direction right);
   otherwise above (direction top). */
function sectionLabelPlacement(f) {
  var coords = (f.geometry && f.geometry.coordinates) || [];
  if (coords.length < 2) return { direction: "top", offset: [0, -6] };
  var pts = coords.map(function (c) {
    var k = Math.cos(c[1] * Math.PI / 180);
    return [c[0] * k, c[1]];
  });
  var total = 0, segs = [];
  for (var i = 1; i < pts.length; i++) {
    var dx = pts[i][0] - pts[i - 1][0], dy = pts[i][1] - pts[i - 1][1];
    var len = Math.sqrt(dx * dx + dy * dy);
    segs.push({ dx: dx, dy: dy, len: len });
    total += len;
  }
  var half = total / 2, acc = 0, chosen = segs[segs.length - 1];
  for (var j = 0; j < segs.length; j++) {
    acc += segs[j].len;
    if (acc >= half) { chosen = segs[j]; break; }
  }
  if (Math.abs(chosen.dy) > Math.abs(chosen.dx)) {
    return { direction: "right", offset: [10, 0] };
  }
  return { direction: "top", offset: [0, -6] };
}

function stretchPopup(f) {
  var p = f.properties;
  var yn = function (b) { return b ? "Yes" : "No crossing recorded"; };
  return "<h3>" + (esc(p.name) || "Chapter section") + "</h3>" + kvTable([
    ["Status", p.has_adopter ? "Adopted" : "Not adopted"],
    ["Adopted by", p.adopter_display ? p.adopter_display.join(", ") : null],
    ["Chapter tracker section", p.tracker_section],
    ["Length (on the official line)",
      p.length_mi != null ? p.length_mi + " mi" : null],
    ["Length (chapter tracker)",
      p.tracker_length_mi != null ? p.tracker_length_mi + " mi" : null],
    ["Access at start", yn(p.access_at_start)],
    ["Access at end", yn(p.access_at_end)],
    ["Access at both ends", p.both_ends_access ? "Yes" : "No"],
  ]);
}

function gapEndAccess(p, which) {
  var trail = which === "start" ? p.nearest_access_start
                                : p.nearest_access_end;
  if (trail) return "Trail crossing: " + trail;
  var road = which === "start" ? p.nearest_road_start : p.nearest_road_end;
  var mi = which === "start" ? p.nearest_road_start_mi
                             : p.nearest_road_end_mi;
  if (road) {
    return "No crossing — nearest road: " + road +
      (mi != null ? " (" + mi + " mi away)" : "");
  }
  return "No access recorded";
}

function gapPopup(f) {
  var p = f.properties;
  var crossings = (p.crossings || []).map(function (c) {
    return c.label + (c.dist_mi != null ? " (" + c.dist_mi + " mi in)" : "");
  }).join("; ");
  return "<h3>" + (esc(p.gap_id) || "Gap") + " — unadopted</h3>" +
    kvTable([
      ["Status", "Unadopted — no section covers this stretch"],
      ["Length", p.length_mi != null ? p.length_mi + " mi" : null],
      ["Land", p.land_context],
      ["Type", p.trail_stat === "off-road" ? "Off-road trail" : p.trail_stat],
      ["West end access", gapEndAccess(p, "start")],
      ["East end access", gapEndAccess(p, "end")],
      ["Trails crossing it", crossings || null],
    ]) + (p.note ? "<p><em>" + esc(p.note) + "</em></p>" : "");
}

/* (The Access points layer was removed Nov 10, 2026 — Paul: "isn't
   great. Let's get rid of it." The computed crossings live on in the
   gazetteer as its Road/Trail crossing entries; the access-points
   data file and its builder remain in the repo.) */

/* Boundary tick bars scale with zoom (see the boundaries layer):
   the group + item list live outside the layer def so layoutTicks()
   can rebuild their geometry on every zoom change. Target: ~22 px
   total on screen, floored at each tick's built length (140 m) so
   zooming IN keeps the original geography. */
var boundaryTickGroup = L.layerGroup();
var boundaryTickItems = [];
var terminusTickItems = [];
function layoutTickSet(items, px) {
  var z = map.getZoom();
  var c = map.getCenter();
  /* Web-Mercator metres per pixel at this latitude/zoom. */
  var mpp = 156543.03392 * Math.cos(c.lat * Math.PI / 180) /
            Math.pow(2, z);
  items.forEach(function (it) {
    /* Grow with zoom-out only up to a cap (Paul, Nov 10, 2026):
       past the cap the bar's geographic size freezes, so zooming
       further out shrinks it on screen instead of letting the bars
       swell until they merge into each other. */
    var target = Math.max(it.baseLen, (it.px || px) * mpp);
    if (it.maxLen) target = Math.min(target, it.maxLen);
    var halfLen = target / 2;
    var ux = it.dir[0], uy = it.dir[1];
    var ul = Math.sqrt(ux * ux + uy * uy) || 1;
    ux /= ul; uy /= ul;
    /* Metres → degrees at the tick's latitude (plate carrée is
       close enough at these lengths). */
    var latHalf = halfLen / 110540;
    var lonHalf = halfLen /
      (111320 * Math.cos(it.center.lat * Math.PI / 180));
    var a = L.latLng(it.center.lat + uy * latHalf,
                     it.center.lng + ux * lonHalf);
    var b = L.latLng(it.center.lat - uy * latHalf,
                     it.center.lng - ux * lonHalf);
    it.casing.setLatLngs([a, b]);
    it.core.setLatLngs([a, b]);
  });
}
function layoutTicks() {
  if (boundaryTickItems.length) layoutTickSet(boundaryTickItems, 22);
  if (terminusTickItems.length) layoutTickSet(terminusTickItems, 56);
}
map.on("zoomend", layoutTicks);

/* Text follows the same rule as the bars (Paul, Nov 10, 2026):
   labels must stop swelling relative to the ground as you zoom
   out, or they merge. Section names shrink a step at a time below
   z12, and a declutter pass hides a name when it would collide
   with a longer section's name nearby (longest sections keep
   their names). Chapter-end labels shrink too but never hide —
   there are only two, at opposite ends of the chapter. */
var sectionLabelItems = [];
function layoutSectionLabels() {
  var z = map.getZoom();
  var font = z >= 12 ? 11 : z === 11 ? 10 : z === 10 ? 9 : 8;
  var placed = [];
  var sorted = sectionLabelItems.slice().sort(function (a, b) {
    return (b.len || 0) - (a.len || 0);
  });
  sorted.forEach(function (it) {
    var tt = it.layer.getTooltip();
    var el = tt && tt.getElement();
    if (!el) return;
    var pt = map.latLngToContainerPoint(it.layer.getCenter());
    var w = it.name.length * font * 0.62 + 8, h = font + 7;
    var collides = placed.some(function (p) {
      return Math.abs(p.x - pt.x) < (p.w + w) / 2 &&
             Math.abs(p.y - pt.y) < (p.h + h) / 2;
    });
    el.style.display = collides ? "none" : "";
    el.style.fontSize = font + "px";
    if (!collides) placed.push({ x: pt.x, y: pt.y, w: w, h: h });
  });
  var tFont = z >= 11 ? 12 : z === 10 ? 11 : 10;
  document.querySelectorAll(".terminus-label span").forEach(
    function (el) { el.style.fontSize = tFont + "px"; });
}
map.on("zoomend", layoutSectionLabels);

/* ------------------------------------------------------------ layers */
/* Each layer: file under data/, builder, default-on flag. Files are
   fetched lazily on first enable. `missingOk` layers (assets)
   quietly show empty when their file is absent. */

var LAYERS = [
  {
    id: "trail", label: "Official trail line", file: "data/trail.geojson",
    onByDefault: true,
    build: function (gj) {
      return L.geoJSON(gj, {
        renderer: canvasFor(),
        style: trailStyle,
        onEachFeature: function (f, l) { l.bindPopup(trailPopup(f)); },
      });
    },
  },
  {
    id: "stretches", label: "Adopted sections",
    file: "data/stretches.geojson", onByDefault: false,
    build: function (gj) {
      var lines = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: STRETCH_STYLE,
        onEachFeature: function (f, l) {
          l.bindPopup(stretchPopup(f));
          /* Section name as a permanent tooltip floating ABOVE
             the line at mid-section (Paul's design correction,
             2026-11-10: names read as floating over their section,
             never stamped on the tread). Leaflet anchors a path
             tooltip at the line's length-centroid. */
          if (f.properties.name) {
            var place = sectionLabelPlacement(f);
            l.bindTooltip(f.properties.name, {
              permanent: true, direction: place.direction,
              offset: place.offset,
              className: "section-name-label", interactive: false,
            });
            sectionLabelItems.push({
              layer: l, name: f.properties.name,
              len: f.properties.length_mi || 0,
            });
          }
          /* Hovering the section (its line or its name — canvas
             paths and the name tooltip's anchor cover both) raises
             the spreadsheet hover card. The gazetteer index loads
             on first hover if it hasn't already. */
          l.on("mouseover", function (e) {
            var show = function () {
              if (sectionHoverTip) {
                map.closeTooltip(sectionHoverTip);
                sectionHoverTip = null;
              }
              sectionHoverTip = L.tooltip({
                sticky: true, direction: "top", offset: [0, -10],
                className: "section-hover-card", opacity: 1,
              }).setLatLng(e.latlng)
                .setContent(sectionHoverHtml(f, f.properties));
              map.openTooltip(sectionHoverTip);
            };
            if (gazFeatures) show(); else gazLoad(show);
          });
          l.on("mouseout", function () {
            if (sectionHoverTip) {
              map.closeTooltip(sectionHoverTip);
              sectionHoverTip = null;
            }
          });
        },
      });
      var group = L.layerGroup([lines]);
      group.bringToFront = function () { lines.bringToFront(); };
      group.on("add", function () {
        window.setTimeout(layoutSectionLabels, 60);
      });
      return group;
    },
  },
  {
    /* Boundary markers ride with the Adopted sections toggle (no
       checkbox of their own): they delineate the adopted sections,
       so they appear when the sections do. Chapter termini are the
       separate "termini" layer below and stay on independently. */
    id: "boundaries", label: "Section boundaries",
    file: "data/boundaries.geojson", onByDefault: false,
    hiddenToggle: true,
    build: function (gj) {
      /* Each boundary is a bar struck ACROSS the line, perpendicular
         to the trail's bearing at that point (tick endpoints computed
         by the site-data build), with NO text: Paul's design
         corrections (2026-11-10): bars, not dots, and nothing
         labelled at segment ends. The bar's length SCALES WITH ZOOM
         (Paul, Nov 10: "the bars need to be larger when zoomed out —
         just big enough to see"): ~22 px on screen at any zoom,
         never shorter than the built 140 m tick; geometry is rebuilt
         on zoomend from each boundary's centre + tick direction.
         White casing under a dark core keeps the tick readable over
         the amber/green lines; drawn on the shared canvas. */
      var items = [];
      gj.features.forEach(function (f) {
        if (f.properties.chapter_end || !f.properties.tick) return;
        var t = f.properties.tick;
        var casing = L.polyline([], { renderer: canvasFor(),
          interactive: false, color: "#ffffff", weight: 6, opacity: 0.9 });
        var core = L.polyline([], { renderer: canvasFor(),
          interactive: false, color: "#263238", weight: 3.5, opacity: 1 });
        items.push({ casing: casing, core: core, feature: f,
          center: L.latLng(f.geometry.coordinates[1],
                           f.geometry.coordinates[0]),
          dir: [t[1][0] - t[0][0], t[1][1] - t[0][1]],
          maxLen: 1600,
          baseLen: map.distance(L.latLng(t[0][1], t[0][0]),
                                L.latLng(t[1][1], t[1][0])) });
        casing.addTo(boundaryTickGroup);
        core.addTo(boundaryTickGroup);
      });
      boundaryTickItems = items;
      layoutTicks();
      return boundaryTickGroup;
    },
  },
  {
    id: "termini", label: "Chapter ends (Itasca Moraine west & east)",
    file: "data/boundaries.geojson", onByDefault: true,
    build: function (gj) {
      var ends = gj.features.filter(function (f) {
        return f.properties.chapter_end;
      });
      ends.sort(function (a, b) {
        return a.geometry.coordinates[0] - b.geometry.coordinates[0];
      });
      var group = L.layerGroup();
      layoutTicks();
      ends.forEach(function (f, i) {
        var c = f.geometry.coordinates;
        var which = i === 0 ? "west end"
          : (i === ends.length - 1 ? "east end" : "end");
        /* The chapter's own ends get the same visual language as
           the section boundaries, with more weight: the tick
           stretched to ~56 px on screen (≈2.5× the section ticks,
           floored at ~280 m), in chapter green with a white casing,
           plus the terminus name (the chapter delineation Paul
           asked for — section ends stay unlabelled, chapter ends
           are labelled). Rebuilt on zoom like the section ticks. */
        if (f.properties.tick) {
          var t = f.properties.tick;
          var casing = L.polyline([], { renderer: canvasFor(),
            interactive: false, color: "#ffffff", weight: 8,
            opacity: 0.9 });
          var core = L.polyline([], { renderer: canvasFor(),
            interactive: false, color: "#1a9850", weight: 5,
            opacity: 1 });
          group.addLayer(casing);
          group.addLayer(core);
          terminusTickItems.push({
            casing: casing, core: core,
            center: L.latLng(c[1], c[0]),
            dir: [t[1][0] - t[0][0], t[1][1] - t[0][1]],
            baseLen: map.distance(L.latLng(t[0][1], t[0][0]),
                                  L.latLng(t[1][1], t[1][0])) * 2,
            px: 56, maxLen: 4200,
          });
        }
        group.addLayer(L.marker([c[1], c[0]], {
          interactive: false, keyboard: false,
          icon: L.divIcon({
            className: "map-label terminus-label", iconSize: [0, 0],
            html: "<span>Itasca Moraine — " + which + "</span>",
          }),
        }));
      });
      return group;
    },
  },
  {
    id: "gaps", label: "Unadopted gap (unclaimed)",
    file: "data/gaps.geojson", onByDefault: true,
    build: function (gj) {
      var bind = function (f, l) { l.bindPopup(gapPopup(f)); };
      var casing = L.geoJSON(gj, { renderer: canvasFor(),
                                   style: GAP_CASING_STYLE,
                                   onEachFeature: bind });
      var core = L.geoJSON(gj, { renderer: canvasFor(),
                                 style: GAP_CORE_STYLE,
                                 onEachFeature: bind });
      var group = L.layerGroup([casing, core]);
      group.bringToFront = function () {
        casing.bringToFront();
        core.bringToFront();
      };
      return group;
    },
  },
  {
    /* parcels disabled Nov 10, 2026 — re-enable by flipping this flag */
    enabled: false,
    id: "parcels", label: "Parcels (owner names — public record)",
    file: "data/parcels.geojson", onByDefault: false,
    build: function (gj) {
      return L.geoJSON(gj, {
        renderer: canvasFor(),
        style: parcelStyle,
        onEachFeature: function (f, l) { l.bindPopup(parcelPopup(f)); },
      });
    },
  },
  {
    id: "access", label: "Access lines (forest roads, OHV, other trails)",
    file: "data/access.geojson", onByDefault: false,
    build: function (gj) {
      return L.geoJSON(gj, {
        renderer: canvasFor(),
        style: accessStyle,
        onEachFeature: function (f, l) { l.bindPopup(accessPopup(f)); },
      });
    },
  },
  {
    id: "roads", label: "Roads", file: "data/roads.geojson",
    onByDefault: false,
    build: function (gj) {
      /* Darker + heavier than the v1–v2 styling (1 px at #999999):
         the data was always there (5,902 MnDOT segments) but
         effectively invisible against the base map (Paul, Nov 10,
         2026: "doesn't seem to have any data"). */
      return L.geoJSON(gj, {
        renderer: canvasFor(),
        style: { color: "#616161", weight: 1.75, opacity: 0.85 },
        onEachFeature: function (f, l) {
          var html = roadPopup(f);
          if (html) l.bindPopup(html);
        },
      });
    },
  },
  {
    id: "assets", label: "Asset pins (photo inventory)",
    file: "data/assets.geojson", onByDefault: true, missingOk: true,
    build: function (gj) {
      return L.geoJSON(gj, {
        pointToLayer: function (f, latlng) {
          return L.circleMarker(latlng, {
            radius: 6, color: "#ffffff", weight: 2,
            fillColor: "#e6550d", fillOpacity: 0.95,
          });
        },
        onEachFeature: function (f, l) { l.bindPopup(assetPopup(f)); },
      });
    },
  },
];

/* The site copy of the inventory lives at site/data/assets.geojson.
   The photo pipeline writes data/assets/assets.geojson in the repo;
   its build step (or a copy) places the site copy here. Until the
   first real batch runs there is no inventory file, and the layer
   simply shows empty. */

var statusEl = document.getElementById("load-status");
var togglesEl = document.getElementById("layer-toggles");

function setStatus(msg) { statusEl.textContent = msg; }

LAYERS.forEach(function (def) {
  def.layer = null;
  def.loading = false;
  if (def.enabled === false) { def.box = null; return; }
  var label = document.createElement("label");
  var box = document.createElement("input");
  box.type = "checkbox";
  box.checked = def.onByDefault;
  label.appendChild(box);
  label.appendChild(document.createTextNode(def.label));
  if (!def.hiddenToggle) togglesEl.appendChild(label);
  def.box = box;
  box.addEventListener("change", function () {
    if (box.checked) { ensureLayer(def, true); }
    else if (def.layer) { map.removeLayer(def.layer); }
    if (def.id === "stretches") syncBoundaries();
  });
  if (def.onByDefault) ensureLayer(def, false);
});

/* Optional URL hash: #layers=access,roads opens with those extra
   layers switched on (handy for sharing a configured view).
   #view=lat,lon,zoom additionally opens at that view instead of
   fitting the whole trail. */
var requestedView = null;
(function applyHash() {
  var hash = location.hash || "";
  var vm = /view=([-\d.]+),([-\d.]+),(\d+(?:\.\d+)?)/.exec(hash);
  if (vm) {
    requestedView = [parseFloat(vm[1]), parseFloat(vm[2])];
    requestedView.push(parseFloat(vm[3]));
  }
  var m = /layers=([a-z,]+)/.exec(hash);
  if (!m) return;
  var wanted = m[1].split(",");
  LAYERS.forEach(function (def) {
    if (def.enabled === false || !def.box) return;
    if (wanted.indexOf(def.id) >= 0 && !def.box.checked) {
      def.box.checked = true;
      ensureLayer(def, false);
    }
  });
  syncBoundaries();
})();

function ensureLayer(def, announce) {
  if (def.enabled === false) return;
  if (def.layer) { def.layer.addTo(map); return; }
  if (def.loading) return;
  def.loading = true;
  if (announce) setStatus("Loading " + def.label + "…");
  fetch(def.file)
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (gj) {
      def.layer = def.build(gj);
      if (def.box && def.box.checked) def.layer.addTo(map);
      if (def.id === "trail") {
        if (requestedView) {
          map.setView([requestedView[0], requestedView[1]],
                      requestedView[2]);
        } else {
          try { map.fitBounds(def.layer.getBounds().pad(0.02)); }
          catch (e) {}
        }
        def.layer.bringToFront();
      }
      def.loading = false;
      setStatus("");
    })
    .catch(function (err) {
      def.loading = false;
      if (def.missingOk) {
        def.layer = L.layerGroup();
        if (def.box && def.box.checked) def.layer.addTo(map);
        setStatus("");
      } else {
        setStatus("Could not load " + def.label + " (" + err.message + ").");
        if (def.box) def.box.checked = false;
      }
    });
}

/* Draw order, re-asserted on every layer add (layers load
   asynchronously): parcels stay at the back; the official line sits
   above them; adopted stretches above the line; the gap above the
   stretches; access-point markers on top of everything so crossings
   stay visible where they coincide with a section or the gap. */
function layerById(id) {
  for (var i = 0; i < LAYERS.length; i++) {
    if (LAYERS[i].id === id) return LAYERS[i];
  }
  return null;
}

/* Section-boundary markers delineate the ADOPTED sections, so they
   follow that layer's toggle (boundaries has no checkbox of its
   own). The chapter termini are independent and stay on. */
function syncBoundaries() {
  var s = layerById("stretches"), b = layerById("boundaries");
  if (!s || !b) return;
  /* Mirror the sections state onto the boundaries def's (hidden)
     checkbox so ensureLayer's add-if-checked logic adds/removes it
     exactly like a user-visible layer. */
  b.box.checked = !!(s.box && s.box.checked);
  if (b.box.checked) { ensureLayer(b, false); }
  else if (b.layer) { map.removeLayer(b.layer); }
}
/* A GeoJSON group add fires "layeradd" once PER FEATURE — 5,902
   times for the roads layer — so re-asserting draw order on every
   event was O(features x reorder) DOM churn on every toggle, the
   main cause of slow layer switches. Coalesce: a burst of events
   schedules ONE re-assertion on the next animation frame. */
var drawOrderQueued = false;
function assertDrawOrder() {
  if (drawOrderQueued) return;
  drawOrderQueued = true;
  requestAnimationFrame(function () {
    drawOrderQueued = false;
    /* Stacking, back → front: access context, roads, the official
       trail line, the ADOPTED SECTIONS on top of the trail line
       (Paul, Nov 10, 2026 — the amber highlight must read as lying
       over the green), the gap, then the boundary ticks and chapter
       ends uppermost so the bars stay visible across everything. */
    ["access", "roads", "trail", "stretches", "gaps",
     "boundaries", "termini"].forEach(function (id) {
      var d = layerById(id);
      if (!d || !d.layer || !map.hasLayer(d.layer)) return;
      if (d.layer.bringToFront) { d.layer.bringToFront(); return; }
      if (d.layer.eachLayer) {
        d.layer.eachLayer(function (l) {
          if (l.bringToFront) l.bringToFront();
        });
      }
    });
    /* Canvas and SVG share the overlay pane as sibling elements;
       keep the SVG element (the point layers) painted above the
       shared canvas regardless of which renderer initialized
       first. */
    var pane = map.getPane("overlayPane");
    var svg = pane && pane.querySelector("svg");
    if (svg && pane.lastChild !== svg) pane.appendChild(svg);
  });
}
map.on("layeradd", assertDrawOrder);

/* ------------------------------------------------------------ legend */

(function buildLegend() {
  var el = document.getElementById("legend");
  var rows = [];
  function add(swatch, text) {
    rows.push("<div class='row'>" + swatch + "<span>" + text + "</span></div>");
  }
  function line(color, dashed) {
    return "<span class='swatch" + (dashed ? " dashed" : "") +
      "' style='border-top-color:" + color + "'></span>";
  }
  add("", "<strong>Trail (official line)</strong>");
  add(line(CHAPTER_COLORS.ITM), "Itasca Moraine Chapter — off-road");
  add(line(CHAPTER_COLORS.ITM, true), "Itasca Moraine Chapter — on-road");
  add(line(CHAPTER_COLORS.LLC), "Laurentian Lakes Chapter — off-road");
  add(line(CHAPTER_COLORS.LLC, true), "Laurentian Lakes Chapter — on-road");
  add("", "<strong>Chapter sections</strong>");
  add(line("#e08214"), "Adopted section (name floats above the line)");
  add(line("#d7301f", true), "Unadopted gap — unclaimed");
  add(line("#263238"),
    "Section boundary — bar across the line (shows with Adopted sections)");
  add(line("#1a9850"),
    "Chapter end — longer bar across the line (Itasca Moraine terminus)");
  add("<span class='swatch pin' style='background:#0570b0'></span>",
      "Access point (trail crossing)");
  add("<span class='swatch pin' style='background:#333333'></span>",
      "Access point (road crossing)");
  /* Parcels legend swatches omitted while the layer is UI-disabled
     (Nov 10, 2026 — see the parcels entry in LAYERS). */
  add("", "<strong>Access</strong>");
  Object.keys(ACCESS_STYLES).forEach(function (k) {
    var s = ACCESS_STYLES[k];
    add(line(s.color, !!s.dashArray), s.label);
  });
  add(line("#999999"), "Roads");
  add("<span class='swatch pin' style='background:#e6550d'></span>",
      "Asset pin (photo inventory)");
  el.innerHTML = rows.join("");
})();

/* ---------------------------------------------------------- corner UI
   The panel's reference material (data sources + legend) lives
   behind two buttons fixed over the map's bottom-left corner, above
   the scale control; the Leaflet attribution (bottom-right) is
   separate and stays visible. Cards start closed, toggle
   independently, and close on a second click. */
(function cornerUi() {
  var ui = document.getElementById("corner-ui");
  if (!ui) return;
  L.DomEvent.disableClickPropagation(ui);
  L.DomEvent.disableScrollPropagation(ui);
  function wire(btnId, cardId) {
    var btn = document.getElementById(btnId);
    var card = document.getElementById(cardId);
    if (!btn || !card) return;
    btn.addEventListener("click", function () {
      var open = card.hidden;
      card.hidden = !open;
      btn.setAttribute("aria-pressed", open ? "true" : "false");
      btn.classList.toggle("active", open);
    });
  }
  wire("btn-sources", "sources-card");
  wire("btn-legend", "legend-card");
})();

/* ---------------------------------------------------------- gazetteer
   The Find box searches site/data/gazetteer.geojson (built by
   scripts/build_gazetteer.py): sections, boundaries, chapter ends,
   crossings, and the NCTA waypoints. The index is fetched lazily
   on first focus — never at page load — and cached, like every
   layer here. Selecting a result flies the map to the point, drops
   a temporary highlight marker, and opens its info card; a section
   result's card carries the section's full tracker record plus its
   contents list (everything the index places inside it). */
var gazFeatures = null;
var gazLoading = false;
var gazMarker = null;

function gazLoad(done) {
  if (gazFeatures) { if (done) done(); return; }
  if (gazLoading) return;
  gazLoading = true;
  fetch("data/gazetteer.geojson")
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (gj) {
      gazFeatures = gj.features || [];
      gazLoading = false;
      if (done) done();
    })
    .catch(function () {
      gazLoading = false;
      setStatus("Could not load the Find index.");
    });
}

function gazSearch(q) {
  var tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length || !gazFeatures) return [];
  return gazFeatures.filter(function (f) {
    var hay = (f.properties.search_text || "").toLowerCase();
    return tokens.every(function (t) { return hay.indexOf(t) >= 0; });
  }).slice(0, 12);
}

function gazContents(sectionName) {
  var byKind = {};
  gazFeatures.forEach(function (f) {
    var p = f.properties;
    if (p.kind === "Section") return;
    var inside = p.section === sectionName ||
      (p.sections && p.sections.indexOf(sectionName) >= 0);
    if (!inside) return;
    (byKind[p.kind] = byKind[p.kind] || []).push(p.name);
  });
  return byKind;
}

function gazPopupHtml(f) {
  var p = f.properties;
  var rows = [
    ["Kind", p.kind],
    ["NCT mile", p.nct_mile != null ? p.nct_mile : null],
    ["Section", p.section],
    ["From the west end",
      p.from_west_mi != null ? p.from_west_mi + " mi along the trail" : null],
    ["From the east end",
      p.from_east_mi != null ? p.from_east_mi + " mi along the trail" : null],
  ];
  if (p.sections && p.sections.length) {
    rows[2] = ["Sections meeting here", p.sections.join(" / ")];
  }
  if (p.off_chain) {
    rows.push(["Position", "Off the depicted chapter chain — nearest " +
      "depicted point ≈ " + (p.snap_m / 1000).toFixed(1) + " km"]);
  }
  if (p.kind !== "Section") {
    rows.push(["Description", p.description]);
    return "<h3>" + (esc(p.name) || "Place") + "</h3>" + kvTable(rows);
  }
  rows = rows.concat([
    ["Description", p.description],
    ["Chapter tracker section", p.tracker_section],
    ["NCT map", p.map_refs ? p.map_refs.join(", ") : null],
    ["NCT miles", p.nct_mile_start != null
      ? p.nct_mile_start + " – " + p.nct_mile_end : null],
    ["Length (on the official line)",
      p.length_mi != null ? p.length_mi + " mi" : null],
    ["Length (chapter tracker)",
      p.tracker_length_mi != null ? p.tracker_length_mi + " mi" : null],
    ["Status", p.has_adopter ? "Adopted" : "Not adopted"],
    ["Adopted by",
      p.adopter_display ? p.adopter_display.join(", ") : null],
    ["Sawyer",
      p.sawyer_display ? p.sawyer_display.join(", ") : null],
    ["2026 maintenance", p.maintenance_2026],
    ["Help requested (as recorded in tracker)",
      p.help_requested != null && p.help_requested !== ""
        ? String(p.help_requested) : null],
    ["Land", p.land_context],
    ["Tracker comments", p.comments],
  ]);
  var html = "<h3>" + (esc(p.name) || "Section") + "</h3>" + kvTable(rows);
  var contents = gazContents(p.name);
  var kinds = Object.keys(contents).sort();
  if (kinds.length) {
    html += "<div class='gaz-contents'><strong>What's here:</strong>";
    kinds.forEach(function (k) {
      var names = contents[k];
      html += "<div>" + esc(k) + " (" + names.length + "): " +
        names.slice(0, 25).map(esc).join("; ") +
        (names.length > 25 ? "; …" : "") + "</div>";
    });
    html += "</div>";
  }
  return html;
}

function gazSelect(f) {
  var c = f.geometry.coordinates;
  var latlng = L.latLng(c[1], c[0]);
  map.flyTo(latlng, Math.max(map.getZoom(), 14), { duration: 0.8 });
  if (gazMarker) map.removeLayer(gazMarker);
  gazMarker = L.circleMarker(latlng, {
    radius: 10, color: "#d7301f", weight: 3,
    fillColor: "#fc8d59", fillOpacity: 0.55,
  }).addTo(map);
  gazMarker.bindPopup(gazPopupHtml(f),
    { maxWidth: f.properties.kind === "Section" ? 380 : 300 });
  window.setTimeout(function () { gazMarker.openPopup(); }, 850);
}

(function gazetteerUi() {
  var input = document.getElementById("gaz-search");
  var box = document.getElementById("gaz-results");
  if (!input || !box) return;
  function hide() { box.hidden = true; box.innerHTML = ""; }
  function render() {
    var results = gazSearch(input.value);
    if (!results.length) { hide(); return; }
    box.innerHTML = "";
    results.forEach(function (f) {
      var p = f.properties;
      var b = document.createElement("button");
      b.type = "button";
      b.className = "gaz-result";
      var mile = p.nct_mile != null ? "NCT " + p.nct_mile
        : (p.off_chain ? "off-chain" : "");
      b.innerHTML = "<strong>" + esc(p.name) + "</strong> " +
        "<span class='gaz-kind'>" + esc(p.kind) + "</span> " +
        "<span class='gaz-mile'>" + esc(mile) + "</span>";
      b.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        hide();
        gazSelect(f);
      });
      box.appendChild(b);
    });
    box.hidden = false;
  }
  input.addEventListener("focus", function () { gazLoad(render); });
  input.addEventListener("input", function () { gazLoad(render); });
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { input.value = ""; hide(); }
    if (ev.key === "Enter") {
      var first = box.querySelector(".gaz-result");
      if (first) first.dispatchEvent(new Event("mousedown"));
    }
  });
  input.addEventListener("blur", function () {
    window.setTimeout(hide, 150);
  });
})();

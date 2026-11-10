/* Itasca Moraine Chapter — Trail Map (working draft), v1.
 *
 * Single-page Leaflet map. Plain script, no build step, no API keys.
 * Data: simplified site copies under data/ (built by
 * scripts/build_site_data.py from the working data in ../data/).
 *
 * PRIVACY: the parcel layer shows parcel ID, county, land class and
 * acres only. Owner names exist in the source corridor file for
 * later chapter working-view tooling, but are stripped from the site
 * copy and are never displayed here. Access popups likewise show
 * names/classes only — maintainer contact fields are stripped too.
 * The segment layers follow the same rule one step further: the
 * site copies of the stretches carry NO adopter names at all (the
 * public-view whitelist in scripts/build_site_data.py reduces the
 * tracker's adopter column to a boolean), and popups show section
 * name, lengths and access only.
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

L.control.layers(
  { "OpenStreetMap": osm, "Topo (OpenTopoMap)": topo }, null,
  { position: "topright" }
).addTo(map);
L.control.scale({ imperial: true, metric: true }).addTo(map);

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

var ACCESS_STYLES = {
  state_forest_road:     { color: "#8c510a", weight: 2,   label: "State forest road" },
  state_park_trail_or_road: { color: "#35978f", weight: 2, label: "State park trail / road" },
  ohv_trail:             { color: "#d7301f", weight: 2,   label: "OHV / ATV-UTV trail" },
  state_trail:           { color: "#2c7fb8", weight: 2.5, label: "State trail" },
  snowmobile_trail:      { color: "#8856a7", weight: 1.5, dashArray: "2 5", label: "Snowmobile trail" },
  hunter_walking_trail:  { color: "#31a354", weight: 1.5, dashArray: "8 4", label: "Hunter walking trail" },
};

function accessStyle(f) {
  var s = ACCESS_STYLES[f.properties.source_type] ||
    { color: "#666666", weight: 1.5 };
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
  ]) + "<p><em>Owner information is not shown on this map.</em></p>";
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

/* Segment popups show section identity, lengths and access only.
   Adopter names are not in the site copy at all (see the header
   privacy note) — "Adopted" is all the public map says. */
function stretchPopup(f) {
  var p = f.properties;
  var yn = function (b) { return b ? "Yes" : "No crossing recorded"; };
  return "<h3>" + (esc(p.name) || "Chapter section") + "</h3>" + kvTable([
    ["Status", p.has_adopter ? "Adopted" : "Not adopted"],
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

function accessPointPopup(f) {
  var p = f.properties;
  var s = ACCESS_STYLES[p.source_type];
  var kindLabel = p.kind === "road" ? "Road crossing"
    : (s ? s.label : "Trail crossing");
  var forWhat = p.for_name
    ? (p.for_type === "gap" ? "Gap " : "Section ") + p.for_name : null;
  return "<h3>" + (esc(p.label) || kindLabel) + "</h3>" + kvTable([
    ["Kind", kindLabel],
    ["For", forWhat],
    ["Position", p.position],
    ["How", p.how === "near" ? "Passes near the end (no crossing)"
                             : "Crosses the trail"],
    ["Distance into section",
      p.dist_from_start_mi != null ? p.dist_from_start_mi + " mi" : null],
  ]);
}

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
        style: trailStyle,
        onEachFeature: function (f, l) { l.bindPopup(trailPopup(f)); },
      });
    },
  },
  {
    id: "stretches", label: "Adopted sections",
    file: "data/stretches.geojson", onByDefault: true,
    build: function (gj) {
      return L.geoJSON(gj, {
        style: STRETCH_STYLE,
        onEachFeature: function (f, l) { l.bindPopup(stretchPopup(f)); },
      });
    },
  },
  {
    id: "gaps", label: "Unadopted gap (unclaimed)",
    file: "data/gaps.geojson", onByDefault: true,
    build: function (gj) {
      var bind = function (f, l) { l.bindPopup(gapPopup(f)); };
      var casing = L.geoJSON(gj, { style: GAP_CASING_STYLE,
                                   onEachFeature: bind });
      var core = L.geoJSON(gj, { style: GAP_CORE_STYLE,
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
    id: "parcels", label: "Parcels (working view — no owner names)",
    file: "data/parcels.geojson", onByDefault: true,
    build: function (gj) {
      return L.geoJSON(gj, {
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
        style: accessStyle,
        onEachFeature: function (f, l) { l.bindPopup(accessPopup(f)); },
      });
    },
  },
  {
    id: "roads", label: "Roads", file: "data/roads.geojson",
    onByDefault: false,
    build: function (gj) {
      return L.geoJSON(gj, {
        style: { color: "#999999", weight: 1, opacity: 0.7 },
        onEachFeature: function (f, l) {
          var html = roadPopup(f);
          if (html) l.bindPopup(html);
        },
      });
    },
  },
  {
    id: "accesspoints", label: "Access points (section crossings)",
    file: "data/access-points.geojson", onByDefault: false,
    build: function (gj) {
      return L.geoJSON(gj, {
        pointToLayer: function (f, latlng) {
          var road = f.properties.kind === "road";
          return L.circleMarker(latlng, {
            radius: road ? 4 : 5, color: "#ffffff", weight: 1.5,
            fillColor: road ? "#333333" : "#0570b0", fillOpacity: 0.95,
          });
        },
        onEachFeature: function (f, l) {
          l.bindPopup(accessPointPopup(f));
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
  var label = document.createElement("label");
  var box = document.createElement("input");
  box.type = "checkbox";
  box.checked = def.onByDefault;
  label.appendChild(box);
  label.appendChild(document.createTextNode(def.label));
  togglesEl.appendChild(label);
  def.box = box;
  box.addEventListener("change", function () {
    if (box.checked) { ensureLayer(def, true); }
    else if (def.layer) { map.removeLayer(def.layer); }
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
    if (wanted.indexOf(def.id) >= 0 && !def.box.checked) {
      def.box.checked = true;
      ensureLayer(def, false);
    }
  });
})();

function ensureLayer(def, announce) {
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
      if (def.box.checked) def.layer.addTo(map);
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
        if (def.box.checked) def.layer.addTo(map);
        setStatus("");
      } else {
        setStatus("Could not load " + def.label + " (" + err.message + ").");
        def.box.checked = false;
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
map.on("layeradd", function () {
  ["trail", "stretches", "gaps", "accesspoints"].forEach(function (id) {
    var d = layerById(id);
    if (d && d.layer && map.hasLayer(d.layer) && d.layer.bringToFront) {
      d.layer.bringToFront();
    }
  });
});

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
  add(line("#e08214"), "Adopted section");
  add(line("#d7301f", true), "Unadopted gap — unclaimed");
  add("<span class='swatch pin' style='background:#0570b0'></span>",
      "Access point (trail crossing)");
  add("<span class='swatch pin' style='background:#333333'></span>",
      "Access point (road crossing)");
  add("", "<strong>Parcels</strong>");
  add("<span class='swatch fill' style='background:#fdbb84'></span>",
      "Parcel the trail crosses");
  add("<span class='swatch fill' style='background:#e7e1c3'></span>",
      "Adjoining parcel (corridor ring)");
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

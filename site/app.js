/* Itasca Moraine Chapter — Trail Map, v7.
 *
 * Single-page Leaflet map. Plain script, no build step, no API keys.
 * Data: simplified site copies under data/ (built by
 * scripts/build_site_data.py from the working data in ../data/).
 *
 * v7 (Nov 10, 2026 — the full cartography build from
 * docs/cartography-notes-2026-11-10.md): corridor-clipped context
 * layers (roads in four classes incl. the moved state forest
 * roads; non-road access with the OHV/hunter colour fixes),
 * zoom-band-stepped weights and kind gates, the unified annotation
 * pass (terminus > gap > section > mile/chainage, with the v6
 * never-touch placement preserved), state mile markers (M2), the
 * chainage measured spine (S1), the marching gap + Carsonite sign
 * chip (S2), base-map casing registers (S3), the Places layer
 * (S4), and Winter/print behaviour (S5).
 *
 * v4 (Nov 10, 2026 — Paul approved the full redesign from
 * docs/design-review/UX-REVIEW.md + DESIGN-REVIEW.md): the section
 * record lives in a persistent INSPECTOR in the left panel, fed by
 * one selection model (click / tap / Find / prev-next / arrow keys).
 * Hover is demoted to a small dwell chip that only advertises the
 * click. The v3 cursor-following full-record hover card and the
 * stretch click popup are deleted.
 *
 * PRIVACY: the parcel layer shows parcel ID, county, land class,
 * acres, and the OWNER name + mailing address exactly as published
 * in the county parcel records — public record, shown per the
 * chapter's 2026-11-10 ruling (see scripts/build_site_data.py); the
 * layer is currently UI-disabled. Maintainer contact fields in the
 * access source data are stripped and never displayed. Adopter
 * names follow the opposite rule: the site copies of the stretches
 * carry PLACEHOLDER names only ("Test adopter 1", "Test adopter 2",
 * ...) assigned by the build script; the real adopter names exist
 * only in the working data and are never copied into any site file.
 *
 * STRUCTURE: layers load lazily the first time their toggle is
 * switched on; each is just an entry in LAYERS below.
 */
"use strict";

/* ------------------------------------------------------- tokens
   Design tokens (DESIGN-REVIEW §1): style.css carries the same
   values as CSS variables; keep the two in step. */
var COLORS = {
  trail: "#1a9850",        /* Itasca Moraine green */
  trailDeep: "#14532d",
  neighbour: "#7e6a9e",    /* Laurentian Lakes, demoted (D2) */
  adopted: "#e08214",
  adoptedDeep: "#6e4400",
  adoptedHover: "#b45f06",
  gap: "#d7301f",
  gapDeep: "#b2182b",
  tick: "#37474f",
  casing: "#ffffff",
  roads: "#616161",
  assetPin: "#e6550d",
};
var CHAPTER_COLORS = { ITM: COLORS.trail, LLC: COLORS.neighbour };
var CHAPTER_NAMES = {
  ITM: "Itasca Moraine Chapter",
  LLC: "Laurentian Lakes Chapter",
};

/* ------------------------------------------------------------- map */

/* Shareable view (Paul, Nov 12, 2026): a #view=lat,lng,zoom link
   opens on that view. Parsed here, before the map exists, so the
   first paint is already the shared view — no flash of the
   default and then a jump. Invalid values fall back to the
   default centre/zoom below. */
var initialView = (function () {
  var m = /view=([-\d.]+),([-\d.]+),(\d+(?:\.\d+)?)/
    .exec(location.hash || "");
  if (!m) return null;
  var lat = parseFloat(m[1]), lng = parseFloat(m[2]),
      z = parseFloat(m[3]);
  if (!isFinite(lat) || !isFinite(lng) || !isFinite(z)) return null;
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  if (z < 0 || z > 19) return null;
  return { center: [lat, lng], zoom: z };
})();

var map = L.map("map", initialView ?
  { center: initialView.center, zoom: initialView.zoom } :
  { center: [47.02, -94.95], zoom: 10 });

/* Zoom ceiling (Paul, Nov 11, 2026 — "one more notch"): each base
   goes one level past its server's native max and upscales the
   native tiles there (maxNativeZoom), same pattern as the LiDAR
   canopy pair — so the map tops out at z18 on the default Topo. */
var topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  maxZoom: 18, maxNativeZoom: 17,
  attribution: "Map data: © OpenStreetMap contributors, SRTM | " +
    "map style: © OpenTopoMap (CC-BY-SA)",
}).addTo(map);

var osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors",
});

/* Base layers. v2 added the MnGeo LiDAR hillshade + aerials; v3 cut
   the USGS shaded relief and the MnGeo spring aerial and added the
   USGS Topo (1:24,000 quadrangle series); v4 makes OpenTopoMap the
   default (DESIGN-REVIEW §2: it flatters the moraine and nothing in
   it mimics the adopted amber), OSM second, and shortens the names
   (UX P5). Endpoints verified live 2026-11-10 — see SOURCES.md. */
var MN_WMS = "https://imageserver.gisdata.mn.gov/cgi-bin/wmswm?";
var mnHillshade = L.tileLayer.wms(MN_WMS, {
  layers: "hillshd", format: "image/jpeg", transparent: false,
  version: "1.1.1",
  attribution: "Shaded relief (LiDAR hillshade): MnGeo / Minnesota DNR",
});
var usgsTopo = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSTopo/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "Topo: USGS, The National Map",
  });
var usgsImagery = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "Aerial imagery: USGS, The National Map (NAIP)",
  });
var esriImagery = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/" +
    "World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 18,
    attribution: "Aerial imagery: Esri, Maxar, Earthstar Geographics",
  });

/* The rest of the nine surviving bases (Nov 11, 2026 prune):
   Paul reviewed the sixteen candidates wired Nov 10 and cut seven
   (Esri World Topo, Stamen Terrain, both CARTO bases,
   Thunderforest Outdoors, Esri World Hillshade, OSM Humanitarian)
   -- the two key-gated definitions and their placeholder keys went
   with them; the map needs no API key for any base. The chooser
   order below is task order, not vendor order: Topographic (the
   working maps) / Relief / Aerial (ground truth) / Streets &
   trails (orientation). See SOURCES.md. */
var usgsImageryTopo = L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/" +
    "USGSImageryTopo/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "Imagery + topo: USGS, The National Map (NAIP)",
  });
var esriNatGeo = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/" +
    "NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: "National Geographic, Esri, DeLorme, HERE, " +
      "UNEP-WCMC, USGS",
  });
var cyclosm = L.tileLayer(
  "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/" +
    "{z}/{x}/{y}.png", {
    subdomains: "abc", maxZoom: 20,
    attribution: "© OpenStreetMap contributors, CyclOSM",
  });

/* Added Nov 11, 2026 (Paul approved the pair): two bases that
   fill the chooser's real gaps -- a winter view and time depth.
   Neither needs a key; both endpoints verified live over the
   chapter the day they landed (see SOURCES.md). */
var esriWayback2014 = L.tileLayer(
  "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
    "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/5844/" +
    "{z}/{y}/{x}", {
    maxZoom: 18,
    attribution: "Aerial imagery (2014): Esri World Imagery " +
      "Wayback, release of 2014-12-30",
  });

/* Winter is a COMPOSED base: OpenSnowMap's pistes are a
   transparent overlay tile set with no cartography of their own
   (OpenSnowMap's own base snow map stays unused -- its author
   discourages outside use), so this radio entry stacks the
   pistes over the MN LiDAR Hillshade, the site's relief
   register. The hillshade layer object is shared with the
   Relief entry: Leaflet moves a layer between parents, never
   duplicates it, so switching between the two entries behaves.
   Verified over the chapter: OSM pistes (nordic ski trails)
   are drawn around Itasca State Park and the Leech Lake shore;
   much of the corridor has none mapped, and there the base
   reads as plain hillshade. */
var snowPistes = L.tileLayer(
  "https://tiles.opensnowmap.org/pistes/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "Snow trails: OpenSnowMap, " +
      "© OpenStreetMap contributors",
  });
var winterBase = L.layerGroup([mnHillshade, snowPistes]);

/* Added Nov 11, 2026 (Paul's LiDAR trio): the 2022
   second-generation LiDAR surfaces, built by
   scripts/build_lidar_trio.py from the state's 2022
   point clouds (first returns) and the seamless 0.5 m DEM,
   clipped to a ~100 m corridor either side of the trail --
   so these two tile sets exist ONLY along the corridor; beyond
   it the tiles simply end (ragged edges are by design).
   Canopy is a grey hillshade of the first-return surface --
   the bare-earth hillshade's sibling, same register.
   Canopy height is canopy-minus-ground as a colour ramp:
   pale at ground level (clearcuts, fields, the tread) to
   deep green at mature-canopy height. Both credit the
   second-generation collection (2021-2024 statewide; the
   corridor blocks were flown spring 2022, leaf-off -- see
   SOURCES.md). Tiles are this repo's own files (site/tiles/),
   z9-15; past z15 the z15 tiles upscale. (z16 was rendered
   and measured -- 152.5 MB for 1,466 tiles -- then dropped:
   the shipped range stays in the tens-of-MB class.)
   Nov 11, 2026 redesign (design review §7): the canopy-height
   colour is ONE overlay ("Tree height") over the base layers,
   not a base — a corridor-only base blanks the world outside
   a 100 m strip and reads as a broken map. The tile layer
   object below serves the overlay; see TREE_HEIGHT below. The
   NW hillshade companion (treeShade) was removed Nov 12, 2026
   (Paul) — the colour alone carries the height. */
var mnCanopyHeight = L.tileLayer(
  "tiles/canopy-height/{z}/{x}/{y}.png", {
    maxZoom: 18, maxNativeZoom: 15,
    bounds: [[46.927759, -95.614014], [47.189712, -94.284668]],
    attribution: "Canopy height (LiDAR, 2022): MnGeo / " +
      "Minnesota DNR",
  });

/* ------------------------------------------------------- Background
   (design review R2): the base-map chooser lives in the panel,
   not in a floating box over the map. Four plain choices —
   Topo (the working map), Aerial (the photo), Terrain (the bare
   ground, no trees), Winter (snow trails) — and the other bases
   behind a "More backgrounds" disclosure for Paul. The two
   canopy radios are retired (see the note above): once Tree
   height exists as an overlay, a corridor-only base is a trap.
   setBase() is the only way the base changes; it keeps the
   imagery label flip, the casing register, and the Winter
   snowmobile emphasis in step (the old Leaflet layers control
   and its baselayerchange handler are gone). */
var BASES = [
  { name: "Topo (OpenTopoMap)", code: "topo", label: "Topo",
    sub: "the working map", layer: topo, primary: true },
  { name: "Aerial (NAIP 2023/25)", code: "aerial", label: "Aerial",
    sub: "the photo", layer: usgsImagery, primary: true },
  { name: "MN LiDAR Hillshade", code: "terrain", label: "Terrain",
    sub: "the bare ground, no trees", layer: mnHillshade,
    primary: true },
  { name: "Winter (snow trails)", code: "winter", label: "Winter",
    sub: "snow trails", layer: winterBase, primary: true,
    winter: true },
  { name: "USGS Topo 1:24k", code: "usgs", label: "USGS Topo",
    sub: "1:24k quadrangles", layer: usgsTopo },
  { name: "National Geographic (Esri)", code: "natgeo", label: "National Geographic",
    sub: "Esri", layer: esriNatGeo },
  { name: "Aerial (Esri)", code: "esri-aerial", label: "Aerial (Esri)",
    sub: "Esri World Imagery", layer: esriImagery },
  { name: "Aerial + Topo (NAIP 2023/25)", code: "aerial-topo", label: "Aerial + Topo",
    sub: "NAIP with topo labels", layer: usgsImageryTopo },
  { name: "Aerial (2014)", code: "aerial-2014", label: "Aerial (2014)",
    sub: "the view at the end of 2014", layer: esriWayback2014 },
  { name: "Streets (OSM)", code: "streets", label: "Streets",
    sub: "OpenStreetMap", layer: osm },
  { name: "Trails (CyclOSM)", code: "trails", label: "Trails",
    sub: "CyclOSM", layer: cyclosm },
  /* Retired Nov 11, 2026 (design review §7): the two canopy
     bases are the Tree height overlay's source now, not
     choices. They stay defined above and are NOT listed here. */
];
var currentBase = BASES[0];

function setBase(name) {
  var def = null;
  BASES.forEach(function (b) { if (b.name === name) def = b; });
  if (!def || def === currentBase) return;
  map.removeLayer(currentBase.layer);
  map.addLayer(def.layer);
  currentBase = def;
  document.body.classList.toggle("base-imagery", /^Aerial/.test(name));
  /* S3 (cartography notes): casing registers — the casing colour
     and register follow the base-map family. LLC never gets a
     casing in any register. Bases not listed default to paper. */
  casingRegister = CASING_BY_BASE[name] || "paper";
  applyCasings();
  /* Winter is a composed base AND a mode: choosing it turns the
     snowmobile emphasis on (heavier snowmobile lines, and they
     survive the print collapse); any other base turns it off.
     (The old standalone Winter checkbox is gone — R7.) */
  winterMode = !!def.winter;
  document.body.classList.toggle("winter", winterMode);
  if (accessLayerRef) accessLayerRef.setStyle(accessStyle);
  markActiveBase(name);
  writeShareHash(); /* a base change is a new shareable view */
}
function markActiveBase(name) {
  document.querySelectorAll("#background-choices .bg-choice, " +
    "#background-more .bg-choice").forEach(function (row) {
    var on = row.getAttribute("data-base") === name;
    row.classList.toggle("on", on);
    row.setAttribute("aria-pressed", on ? "true" : "false");
  });
}
/* Shareable view: look a base up by its short hash code. */
function baseByCode(code) {
  for (var i = 0; i < BASES.length; i++) {
    if (BASES[i].code === code) return BASES[i];
  }
  return null;
}
(function buildBackground() {
  function rowFor(def) {
    /* A real button (aria-pressed + the "on" class), not a
       label + radio — the Background section is a set of
       actions, and the radio's checked state drifted from
       the "on" class markActiveBase maintains. */
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "bg-choice";
    btn.setAttribute("data-base", def.name);
    btn.setAttribute("aria-pressed",
      def === currentBase ? "true" : "false");
    if (def === currentBase) btn.classList.add("on");
    btn.textContent = def.label + " ";
    var sub = document.createElement("span");
    sub.className = "bg-sub";
    sub.textContent = "— " + def.sub;
    btn.appendChild(sub);
    btn.addEventListener("click", function () {
      setBase(def.name);
    });
    return btn;
  }
  var main = document.getElementById("background-choices");
  var more = document.getElementById("background-more");
  var moreBtn = document.getElementById("bg-more-btn");
  if (!main || !more) return;
  BASES.forEach(function (def) {
    (def.primary ? main : more).appendChild(rowFor(def));
  });
  if (moreBtn) {
    moreBtn.addEventListener("click", function () {
      var open = more.hidden;
      more.hidden = !open;
      moreBtn.textContent = open ? "Fewer backgrounds…"
                                 : "More backgrounds…";
    });
  }
})();
L.control.scale({ imperial: true, metric: true }).addTo(map);

/* ------------------------------------------------ v7 cartography
   Zoom bands (cartography notes §2): Z1 ≤ 10 (chapter), Z2 11–12
   (district), Z3 13–14 (section), Z4 ≥ 15 (ground). Weights, kind
   visibility and label classes step at these bands. */
var currentBand = 1;
function zoomBand() {
  var z = map.getZoom();
  return z <= 10 ? 1 : z <= 12 ? 2 : z <= 14 ? 3 : 4;
}

/* S3 casing registers, exactly the spec table. `bump` is the
   relief register's +0.5 weight lift on cased layers. */
var CASING_REGISTERS = {
  paper:  { color: "#f7f5ee", trail: 0.45, amber: 0.4,  gap: 0.4,  bump: 0 },
  photo:  { color: "#ffffff", trail: 0.85, amber: 0.75, gap: 0.55, bump: 0 },
  relief: { color: "#f7f5ee", trail: 0.6,  amber: 0.5,  gap: 0.5,  bump: 0.5 },
};
var CASING_BY_BASE = {
  "Topo (OpenTopoMap)": "paper",
  "Streets (OSM)": "paper",
  "Trails (CyclOSM)": "paper",
  "Aerial (NAIP 2023/25)": "photo",
  "Aerial (Esri)": "photo",
  "Aerial + Topo (NAIP 2023/25)": "photo",
  "Aerial (2014)": "photo",
  "Winter (snow trails)": "relief",
  "MN LiDAR Hillshade": "relief",
  /* The two canopy bases are retired (design review §7): their
     tile sets are the Tree height overlay's source now, not
     bases, so they have no casing register entry. */
  "USGS Topo 1:24k": "relief",
  "National Geographic (Esri)": "relief",
};
var casingRegister = "paper";

/* Layer internals the zoom/print/casing machinery restyles. */
var trailCasingLayer = null, trailCoreLayer = null;
var stretchCasingLayer = null, stretchLinesLayer = null;
var gapCasingLayer = null, gapCoreLayer = null, gapsGroupRef = null;
var accessLayerRef = null, roadsGroupRef = null, parcelsLayerRef = null;
var printMode = false;
var winterMode = false;

function applyCasings() {
  if (trailCasingLayer) trailCasingLayer.setStyle(trailCasingStyle);
  if (stretchCasingLayer) {
    stretchCasingLayer.setStyle(stretchCasingStyle);
  }
  if (gapCasingLayer) gapCasingLayer.setStyle(gapCasingStyle);
}

/* Zoom-stepped restyles (§2.1–2.3 weights, §2.5 tick fade, §2.8
   parcel gate via parcelStyle, §2.9/§2.10 band gates via the style
   functions) plus the Places Z3 gate and the annotation pass. */
function applyZoomStyles() {
  currentBand = zoomBand();
  var z = map.getZoom();
  if (trailCoreLayer) trailCoreLayer.setStyle(trailStyle);
  if (trailCasingLayer) trailCasingLayer.setStyle(trailCasingStyle);
  if (stretchLinesLayer) stretchLinesLayer.setStyle(stretchStyle);
  if (accessLayerRef) accessLayerRef.setStyle(accessStyle);
  if (roadsGroupRef) {
    roadsGroupRef.eachLayer(function (l) { l.setStyle(roadStyle); });
  }
  if (parcelsLayerRef) parcelsLayerRef.setStyle(parcelStyle);
  /* §2.5: section ticks fade to 0.55 in band Z1 and are not
     rendered at z ≤ 8; termini ticks are unchanged. */
  var tickOp = z <= 8 ? 0 : (currentBand === 1 ? 0.55 : 1);
  boundaryTickItems.forEach(function (it) {
    it.core.setStyle({ opacity: tickOp });
    it.casing.setStyle({ opacity: tickOp === 0 ? 0 : 0.85 });
  });
  applyPlacesGate();
  applyContoursGate();
}
map.on("zoomend", applyZoomStyles);

/* S4: Places draw at Z3+ only — the gate swaps the marker group
   in and out of its layer as the zoom crosses 13. */
var placesInnerRef = null, placesOuterRef = null;
function applyPlacesGate() {
  if (!placesInnerRef || !placesOuterRef) return;
  var show = map.getZoom() >= 13;
  if (show && !placesOuterRef.hasLayer(placesInnerRef)) {
    placesOuterRef.addLayer(placesInnerRef);
  }
  if (!show && placesOuterRef.hasLayer(placesInnerRef)) {
    placesOuterRef.removeLayer(placesInnerRef);
  }
}

/* Rotated image overlays — vendored from IvanSanchez /
   Leaflet.ImageOverlay.Rotated (Beerware license, Ivan Sanchez
   Ortega <ivan@sanchezortega.es>), pasted verbatim in logic and
   re-indented to this file's style. Stock L.imageOverlay can only
   draw an axis-aligned rectangle; this subclass places an image by
   three corners (top-left, top-right, bottom-left) and lets the
   browser apply the affine transform, so a sheet image lands on
   its true leaning UTM frame instead of the frame's axis-aligned
   box. Added Nov 11, 2026 for the NCTA map sheets (docs/
   research-sheets-alignment-2026-11-11.md): the old axis-aligned
   placement sheared printed content 80-150 m, 103-256 m at
   corners; the affine placement leaves <= ~9 m residual. */
L.ImageOverlay.Rotated = L.ImageOverlay.extend({
  initialize: function (image, topleft, topright, bottomleft, options) {
    if (typeof (image) === "string") {
      this._url = image;
    } else {
      /* Assume that the first parameter is an instance of
         HTMLImage or HTMLCanvas. */
      this._rawImage = image;
    }
    this._topLeft = L.latLng(topleft);
    this._topRight = L.latLng(topright);
    this._bottomLeft = L.latLng(bottomleft);
    L.setOptions(this, options);
  },

  onAdd: function (map) {
    if (!this._image) {
      this._initImage();
      if (this.options.opacity < 1) {
        this._updateOpacity();
      }
    }
    if (this.options.interactive) {
      L.DomUtil.addClass(this._rawImage, "leaflet-interactive");
      this.addInteractiveTarget(this._rawImage);
    }
    map.on("zoomend resetview", this._reset, this);
    this.getPane().appendChild(this._image);
    this._reset();
  },

  onRemove: function (map) {
    map.off("zoomend resetview", this._reset, this);
    L.ImageOverlay.prototype.onRemove.call(this, map);
  },

  _initImage: function () {
    var img = this._rawImage;
    if (this._url) {
      img = L.DomUtil.create("img");
      /* Hide while the first transform (zero or one frames) is
         being done. */
      img.style.display = "none";
      if (this.options.crossOrigin) {
        img.crossOrigin = "";
      }
      img.src = this._url;
      this._rawImage = img;
    }
    L.DomUtil.addClass(img, "leaflet-image-layer");
    /* this._image is reused by some of the methods of the parent
       class and must keep the name, even if it is
       counter-intuitive. */
    var div = this._image = L.DomUtil.create("div",
      "leaflet-image-layer " +
      (this._zoomAnimated ? "leaflet-zoom-animated" : ""));
    this._updateZIndex(); /* apply z-index style setting to the div
                             (if defined) */
    div.appendChild(img);
    div.onselectstart = L.Util.falseFn;
    div.onmousemove = L.Util.falseFn;
    img.onload = function () {
      this._reset();
      img.style.display = "block";
      this.fire("load");
    }.bind(this);
    img.alt = this.options.alt;
  },

  _reset: function () {
    var div = this._image;
    /* Project control points to container-pixel coordinates. */
    var pxTopLeft = this._map.latLngToLayerPoint(this._topLeft);
    var pxTopRight = this._map.latLngToLayerPoint(this._topRight);
    var pxBottomLeft = this._map.latLngToLayerPoint(this._bottomLeft);
    /* Infer coordinate of bottom right. */
    var pxBottomRight = pxTopRight.subtract(pxTopLeft).add(pxBottomLeft);
    /* pxBounds is mostly for positioning the <div> container. */
    var pxBounds = L.bounds([pxTopLeft, pxTopRight, pxBottomLeft,
      pxBottomRight]);
    var size = pxBounds.getSize();
    var pxTopLeftInDiv = pxTopLeft.subtract(pxBounds.min);
    /* Calculate the skew angles, both in X and Y. */
    var vectorX = pxTopRight.subtract(pxTopLeft);
    var vectorY = pxBottomLeft.subtract(pxTopLeft);
    var skewX = Math.atan2(vectorX.y, vectorX.x);
    var skewY = Math.atan2(vectorY.x, vectorY.y);
    /* LatLngBounds used for animations. */
    this._bounds = L.latLngBounds(
      this._map.layerPointToLatLng(pxBounds.min),
      this._map.layerPointToLatLng(pxBounds.max));
    L.DomUtil.setPosition(div, pxBounds.min);
    div.style.width = size.x + "px";
    div.style.height = size.y + "px";
    var imgW = this._rawImage.width;
    var imgH = this._rawImage.height;
    if (!imgW || !imgH) {
      return; /* Probably because the image hasn't loaded yet. */
    }
    var scaleX = pxTopLeft.distanceTo(pxTopRight) / imgW *
      Math.cos(skewX);
    var scaleY = pxTopLeft.distanceTo(pxBottomLeft) / imgH *
      Math.cos(skewY);
    this._rawImage.style.transformOrigin = "0 0";
    this._rawImage.style.transform =
      "translate(" + pxTopLeftInDiv.x + "px, " +
      pxTopLeftInDiv.y + "px)" +
      "skew(" + skewY + "rad, " + skewX + "rad) " +
      "scale(" + scaleX + ", " + scaleY + ") ";
  },

  reposition: function (topleft, topright, bottomleft) {
    this._topLeft = L.latLng(topleft);
    this._topRight = L.latLng(topright);
    this._bottomLeft = L.latLng(bottomleft);
    this._reset();
  },

  setUrl: function (url) {
    this._url = url;
    if (this._rawImage) {
      this._rawImage.src = url;
    }
    return this;
  },
});

L.imageOverlay.rotated = function (imgSrc, topleft, topright,
  bottomleft, options) {
  return new L.ImageOverlay.Rotated(imgSrc, topleft, topright,
    bottomleft, options);
};

/* NCTA map sheets: the 22 sheet IMAGES draw at zoom 11+ only —
   below that the toggle shows just the sheet outlines and number
   labels (a locator), so the chapter view is never buried under
   a near-white blanket. Leaflet loads an image overlay's <img>
   only while the layer is on the map, so gating here also keeps
   the 13 MB of sheet JPEGs off the wire until they can be read. */
var sheetImages = [];
function applySheetImageGate() {
  var show = map.getZoom() >= 11;
  sheetImages.forEach(function (img) {
    var onMap = img._map != null;
    if (show && !onMap && img._sheetGroup &&
        map.hasLayer(img._sheetGroup)) {
      img._sheetGroup.addLayer(img);
    }
    if (!show && onMap) img._sheetGroup.removeLayer(img);
  });
}
map.on("zoomend", applySheetImageGate);

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

var COARSE_POINTER = !!(window.matchMedia &&
  window.matchMedia("(pointer: coarse)").matches);

/* ------------------------------------------------------------ style */

function isOnRoad(p) {
  return p.trail_stat === "NCT (on-road)" || p.trail_type === "Public Road";
}

/* §2.1/§2.2 (v7): zoom-stepped weights. ITM: 3.5 in Z1, 4 in
   Z2–Z3, 5 in Z4, opacity 0.9; an on-road stretch of either chain
   goes dotted ("2 7", round caps, weight 3 for ITM). LLC stays
   demoted: #7e6a9e, weight 2.5, opacity 0.7, and NO casing in any
   register (its casing is simply never drawn — see the trail
   layer build, which casings only ITM... both chains share the
   casing layer; the LLC casing is suppressed per-feature here). */
function trailStyle(f) {
  var p = f.properties;
  var onRoad = isOnRoad(p);
  if (p.chapter === "LLC") {
    return {
      color: COLORS.neighbour, weight: 2.5, opacity: 0.7,
      dashArray: onRoad ? "2 7" : null, lineCap: "round",
    };
  }
  return {
    color: COLORS.trail,
    weight: onRoad ? 3
      : (currentBand === 1 ? 3.5 : currentBand === 4 ? 5 : 4),
    opacity: 0.9,
    dashArray: onRoad ? "2 7" : null, lineCap: "round",
  };
}

/* Casing under the official line (DESIGN D1), restyled by the S3
   register of the active base. LLC features get a fully
   transparent casing — the neighbour chain never carries one. */
function trailCasingStyle(f) {
  if (f.properties.chapter === "LLC") {
    return { color: "#ffffff", weight: 0, opacity: 0, dashArray: null };
  }
  var reg = CASING_REGISTERS[casingRegister];
  return {
    color: reg.color,
    weight: (isOnRoad(f.properties) ? 5.5 : 7) + reg.bump,
    opacity: reg.trail,
    dashArray: null,
  };
}

/* Non-road access (§2.9, v7): kind table with the two colour fixes
   (OHV burnt orange #a63603 — the old #d7301f WAS the gap red;
   hunter-walking sage #6e8b67 — the old green sat on the trail
   green) and per-kind zoom-band gates. Weights are the Z3 values;
   Z2 reads 20% lighter. Layer opacity 0.75 except park (0.65).
   State forest roads are no longer here — they draw as Roads
   class F (§2.9 move). Weights raised across the table Nov 10,
   2026 (Paul: "roads and non road access should be heavier
   lines") — colours, dashes, opacities and band gates unchanged. */
var ACCESS_STYLES = {
  state_park_trail_or_road: { color: "#35978f", weight: 1.6, opacity: 0.65, minBand: 3, label: "State park trail / road" },
  ohv_trail:             { color: "#a63603", weight: 1.75, dashArray: "6 3 1.5 3", minBand: 2, label: "OHV / ATV-UTV trail" },
  state_trail:           { color: "#2c7fb8", weight: 2.25, minBand: 1, label: "State trail" },
  snowmobile_trail:      { color: "#8856a7", weight: 1.4, dashArray: "2 5", minBand: 2, label: "Snowmobile trail" },
  hunter_walking_trail:  { color: "#6e8b67", weight: 1.4, dashArray: "8 4", minBand: 3, label: "Hunter walking trail" },
};
var ACCESS_DEFAULT = { color: "#666666", weight: 1.75, minBand: 1,
                       label: "Access line" };

function accessStyle(f) {
  var s = ACCESS_STYLES[f.properties.source_type] || ACCESS_DEFAULT;
  if (printMode) return printAccessStyle(f, s);
  if (currentBand < (s.minBand || 1)) {
    return { color: s.color, weight: 0, opacity: 0, dashArray: null };
  }
  var w = s.weight;
  if (currentBand === 2) w = Math.max(0.75, w * 0.8);
  var dash = s.dashArray || null;
  /* S5 Winter: snowmobile promoted on screen when the season
     toggle is on (weight + filled-season dash). */
  if (winterMode && f.properties.source_type === "snowmobile_trail") {
    w = 2; dash = "4 2";
  }
  return { color: s.color, weight: w,
           opacity: s.opacity != null ? s.opacity : 0.75,
           dashArray: dash };
}

/* S5 print collapse for access: state trail only, as a solid
   hairline; snowmobile survives only in Winter mode. */
function printAccessStyle(f, s) {
  var t = f.properties.source_type;
  if (t === "state_trail") {
    return { color: s.color, weight: 1.75, opacity: 0.9, dashArray: null };
  }
  if (winterMode && t === "snowmobile_trail") {
    return { color: s.color, weight: 2, opacity: 0.9,
             dashArray: "4 2" };
  }
  return { color: s.color, weight: 0, opacity: 0, dashArray: null };
}

/* §2.8 (v7): parcels restyled for the layer's return — re-enabled
   Nov 10, 2026 (evening) as an off-by-default, lazy-loaded layer;
   styles apply only at Z3+. */
function parcelStyle(f) {
  if (currentBand < 3) {
    return { color: "#a89a5b", weight: 0, opacity: 0, fillOpacity: 0 };
  }
  var crossed = f.properties.corridor === "crossed";
  return {
    color: crossed ? "#b35806" : "#a89a5b",
    weight: crossed ? 1 : 0.5,
    dashArray: crossed ? null : "3 3",
    fillColor: crossed ? "#fdbb84" : "#e7e1c3",
    fillOpacity: crossed ? 0.32 : 0.12,
  };
}

/* Adopted stretches (§2.3, v7): amber #e08214 at opacity 1,
   weight 6 in Z1–Z3 and 5 in Z4 (the line is fully in view at
   ground zoom, so the highlight can afford to be calmer). The
   casing under them is register-driven (S3). */
var STRETCH_STYLE = { color: COLORS.adopted, opacity: 1 };
function stretchStyle() {
  return { color: COLORS.adopted,
           weight: currentBand === 4 ? 5 : 6, opacity: 1 };
}
function stretchCasingStyle() {
  var reg = CASING_REGISTERS[casingRegister];
  return { color: reg.color, weight: 8.5 + reg.bump, opacity: reg.amber };
}
var STRETCH_HOVER_STYLE = { color: COLORS.adoptedHover, weight: 8, opacity: 1 };

/* Roads (§2.10, v7): four classes derived in the site build from
   the centreline route_sys codes + name patterns (cartoclass is
   null in the source; class F is the moved state forest roads).
   No road name labels on the face, ever. The cut feather: a
   corridor-clipped feature (cut:true) draws at 0.6× its class
   opacity — the visible cue for "this line continues". */
var ROAD_CLASS_STYLES = {
  A: { color: "#616161", weight: 2.75, opacity: 0.85, minBand: 1,
       label: "Arterial — trunk highway / county state-aid",
       short: "Roads — trunk / county state-aid" },
  B: { color: "#83837a", weight: 2, opacity: 0.7, minBand: 2,
       label: "Local road", short: "Roads — local" },
  C: { color: "#a9a396", weight: 1.5, opacity: 0.55, minBand: 3,
       label: "Minor road — township / unnamed",
       short: "Roads — minor / township" },
  F: { color: "#8c510a", weight: 1.75, opacity: 0.8, minBand: 2,
       label: "State forest road", short: "State forest road" },
};
var ROADS_STYLE = ROAD_CLASS_STYLES.A;

function roadStyle(f) {
  var p = f.properties;
  var s = ROAD_CLASS_STYLES[p.road_class] || ROAD_CLASS_STYLES.C;
  if (printMode) {
    /* S5 print collapse: classes A + F only, in one grey. */
    if (p.road_class === "A") {
      return { color: "#616161", weight: 2.2, opacity: 0.9,
               dashArray: null };
    }
    if (p.road_class === "F") {
      return { color: "#616161", weight: 2, opacity: 0.9,
               dashArray: null };
    }
    return { color: "#616161", weight: 0, opacity: 0, dashArray: null };
  }
  if (currentBand < (s.minBand || 1)) {
    return { color: s.color, weight: 0, opacity: 0, dashArray: null };
  }
  return { color: s.color, weight: s.weight,
           opacity: s.opacity * (p.cut ? 0.6 : 1), dashArray: null };
}

/* The unadopted gap is the recruiting layer — it must be the most
   visible line on the map: a deep-red casing under a bold dashed
   red core (the closest plain Leaflet gets to a hatched line).
   The core's dashes MARCH westward while the layer is on (S2). */
function gapCasingStyle() {
  var reg = CASING_REGISTERS[casingRegister];
  return { color: COLORS.gapDeep, weight: 11 + reg.bump,
           opacity: reg.gap };
}
var GAP_CORE_STYLE = {
  color: COLORS.gap, weight: 5, opacity: 1, dashArray: "14 8",
  dashOffset: "0",
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

/* Every retained popup gets the same guard (UX P9): internal scroll
   past 70 vh and breathing room from the panel/controls. */
function bindPop(layer, html, maxWidth) {
  layer.bindPopup(html, {
    maxWidth: maxWidth || 300,
    maxHeight: Math.round(window.innerHeight * 0.7),
    autoPanPadding: [24, 24],
  });
}

/* Name-tag door (pop-up spec §5): a gazetteer point whose `section`
   names a section gets one door at the foot of its card — "Open
   {Section} record" — which closes the popup and runs the same
   selection path Find uses. Wired by delegation on the popup pane
   so popup/gazetteer-marker/What's-here doors all share it. */
document.addEventListener("click", function (e) {
  var t = e.target;
  if (!t || !t.classList || !t.classList.contains("pop-door")) return;
  var name = t.getAttribute("data-section");
  if (!name) return;
  map.closePopup();
  var f = gazFeatureByName(name, "Section");
  if (f) gazSelectSection(f);
});

/* Asset-pin face flip (Nov 11, 2026): the popup shows one face at a
   time; the buttons swap the large image and the face label, and
   "Show all photos" opens the full grid. Same document-level
   delegation as the pop-door above. */
document.addEventListener("click", function (e) {
  var t = e.target;
  if (!t || !t.classList) return;
  if (t.classList.contains("pop-face")) {
    var wrap = t.closest(".pop-flip");
    if (!wrap) return;
    var img = wrap.querySelector(".pop-face-img");
    var d = t.getAttribute("data-derivative");
    if (img && d) img.setAttribute("src", "assets-photos/" + d);
    var label = wrap.querySelector(".pop-face-label");
    if (label) {
      var lab = t.getAttribute("data-label") || "";
      var dat = t.getAttribute("data-date") || "";
      label.textContent = lab + (dat ? " · " + dat : "");
    }
    var btns = wrap.querySelectorAll(".pop-face");
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle("active", btns[i] === t);
    }
    return;
  }
  if (t.classList.contains("pop-faces-all")) {
    var w = t.closest(".pop-flip");
    if (!w) return;
    var grid = w.querySelector(".pop-face-grid");
    if (!grid) return;
    var open = grid.style.display !== "none";
    grid.style.display = open ? "none" : "flex";
    t.textContent = open ? "Show all photos" : "Hide all photos";
  }
});

function gazFeatureByName(name, kind) {
  if (!gazFeatures) return null;
  for (var i = 0; i < gazFeatures.length; i++) {
    var f = gazFeatures[i];
    if (f.properties.name === name &&
        (!kind || f.properties.kind === kind)) return f;
  }
  return null;
}

function trailPopup(f) {
  var p = f.properties;
  var title = esc(p.seg_name) || "North Country Trail";
  var kind = p.trail_stat === "NCT (on-road)" ? "On-road section" : "Off-road trail";
  return "<h3>" + title + "</h3>" + kvTable([
    ["Chapter", CHAPTER_NAMES[p.chapter] || p.chapter],
    ["Type", kind + (p.trail_type ? " (" + p.trail_type + ")" : "")],
    ["Source", "North Country Trail Association — official trail line"],
  ]);
}

function parcelPopup(f) {
  var p = f.properties;
  return "<h3>Parcel " + (esc(p.parcel_id) || "—") + "</h3>" + kvTable([
    ["County", p.county],
    ["Land class", p.land_class],
    ["Acres", p.acres],
    ["Owner", p.owner],
    ["Source", "County parcel records — public record"],
  ]);
}

/* Leech Lake Reservation: name the nation and the source, give the
   trail fact that makes the layer worth switching on, and carry
   the honest line — the federal boundary as published, not a
   legal survey. */
function leechLakePopup(f) {
  var p = f.properties;
  var trail = (p.trail_miles_inside != null)
    ? p.trail_miles_inside + " mi of the depicted trail lies " +
      "inside the reservation (" +
      (p.trail_sections_inside || []).join(", ") + ")"
    : null;
  return "<h3>Leech Lake Reservation</h3>" + kvTable([
    ["Nation", p.band],
    ["Boundary", p.source],
    ["Vintage", p.vintage],
    ["Area", p.area_acres != null
      ? Number(p.area_acres).toLocaleString("en-US") + " acres" : null],
    ["Trail inside", trail],
  ]) + "<p class='pop-note'>" + esc(p.note) + "</p>";
}
/* Logging and burns (Phase 3, Nov 12, 2026): three layers from
   the county / DNR / federal pull in working/logging-burns/ —
   Cass County timber sales, Cass FIM stands, and the USFS EDW
   timber sale on the Chippewa NF. The sources carry no expiry
   or status, so the popups show the year prominently instead
   of implying a sale is current; a sale's year is the
   freshness signal. FIM stand_age 0 means unrecorded, not
   age 0. */
/* Source link lines (Paul, Nov 12, 2026): kvTable escapes HTML,
   so a clickable source cannot live in the table — it is
   appended as its own line. Each URL is the service's own
   page, verified live (HTTP 200, Nov 12, 2026). */
var SRC_CASS_TIMBER = "https://cassweb.casscountymn.gov/arcgis/" +
  "rest/services/Forestry_ForestPlan_Base/MapServer/62";
var SRC_CASS_FIM = "https://cassweb.casscountymn.gov/arcgis/" +
  "rest/services/Forestry_ForestPlan_Base/MapServer/63";
var SRC_EDW = "https://apps.fs.usda.gov/arcx/rest/services/EDW/" +
  "EDW_ActivityProjectAreas_01/MapServer/2";
var SRC_EASEMENTS = "https://apps.bwsr.state.mn.us/arcgis/" +
  "rest/services/RIM/RIM_Reserve_Easements/MapServer/0";
function popSourceLine(url, label) {
  return "<p class='pop-source'>Source: <a href='" + url +
    "' target='_blank' rel='noopener'>" + esc(label) + "</a></p>";
}
/* Timber sale style (Paul, Nov 12, 2026): recent sales
   (2024–2026 — 113 Cass, 20 Chippewa NF) render amber and
   highlighted; older sales keep the layer's standard style
   (std). A sale with no year renders as older. */
function timberSaleStyle(f, std) {
  var y = (f.properties || {}).year;
  if (typeof y === "number" && y >= 2024) {
    return {
      color: "#92400e", weight: 2,
      fillColor: "#f59e0b", fillOpacity: 0.45,
    };
  }
  return {
    color: std.color, weight: std.weight,
    fillColor: std.fillColor, fillOpacity: std.fillOpacity,
  };
}
function logCassPopup(f) {
  var p = f.properties;
  return "<h3>" + esc(p.name || "Timber sale") + "</h3>" + kvTable([
    ["Permit", p.permit],
    ["Acres", p.acres],
    ["Year", p.year],
  ]) + "<p class='pop-note'>No expiry in the source — the year " +
    "is the sale year, not a guarantee the sale is current.</p>" +
    popSourceLine(SRC_CASS_TIMBER,
      "Cass County Forestry Web Map — Timber Sales (Current), layer 62");
}
function logFimPopup(f) {
  var p = f.properties;
  var age = (p.stand_age == null || p.stand_age === 0)
    ? "not recorded" : p.stand_age;
  var trs = [p.township, p.range, p.section].filter(function (v) {
    return v != null;
  }).join(" / ");
  return "<h3>" + esc(p.name || "Forest stand") + "</h3>" + kvTable([
    ["Cover type", p.cover_type],
    ["Acres", p.acres],
    ["Stand age", age],
    ["Timber status", p.timber_status],
    ["Native plant community", p.npc],
    ["Year", p.year],
    ["Township / Range / Section", trs || null],
  ]) + "<p class='pop-note'>Forest inventory stand, not a sale.</p>" +
    popSourceLine(SRC_CASS_FIM,
      "Cass County Forestry Web Map — FIM Stands (Current), layer 63");
}
function logEdwPopup(f) {
  var p = f.properties;
  return "<h3>" + esc(p.name || "Timber sale") + "</h3>" + kvTable([
    ["Contract", p.permit],
    ["Acres", p.acres],
    ["Year", p.year],
    ["Revised", p.rev_date],
    ["Forest", p.forest],
    ["District", p.district],
  ]) + "<p class='pop-note'>Revised is the last revision date, " +
    "not an expiry — the source carries none.</p>" +
    popSourceLine(SRC_EDW,
      "USFS EDW Activity Project Areas — Timber Sale, " +
      "Chippewa National Forest");
}
/* Conservation easements (Nov 12, 2026): BWSR RIM Reserve
   easements clipped to the corridor (40 easements, 3,370 ac —
   38 perpetual riparian, 1 limited cropland, 1 PWP). One
   easement is expired and is carried honestly with its expiry
   shown, not hidden. */
function easementsPopup(f) {
  var p = f.properties;
  var rows = [
    ["Type", p.type],
    ["Acres", p.acres],
    ["Program", p.program],
    ["County", p.county],
    ["Recorded", p.recorded],
    ["Perpetual", p.perpetual ? "Yes" : "No"],
    ["Status", p.status],
  ];
  if (p.status === "expired" && p.expires) {
    rows.splice(6, 0, ["Expired", p.expires]);
  }
  return "<h3>" + esc(p.name || "Conservation easement") + "</h3>" +
    kvTable(rows) +
    popSourceLine(SRC_EASEMENTS,
      "BWSR RIM Reserve Easements, MapServer layer 0");
}


/* Trail alerts (NCTA trail_alerts service, pulled by
   scripts/pull_trail_alerts.py): the alert's own title, date and
   description, quoted verbatim — the map never rewrites an alert.
   The stored `date` is the intended calendar date (the service
   stores UTC midnight of the following day; the pull derives the
   America/Chicago date — see the pull script's header). */
var ALERT_MONTHS = ["January", "February", "March", "April", "May",
  "June", "July", "August", "September", "October", "November",
  "December"];

function alertDateText(p) {
  if (p.date) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(p.date);
    if (m) {
      return ALERT_MONTHS[parseInt(m[2], 10) - 1] + " " +
        parseInt(m[3], 10) + ", " + m[1];
    }
    return p.date;
  }
  if (p.date_ms != null) {
    return new Date(p.date_ms).toLocaleDateString("en-US", {
      timeZone: "America/Chicago", year: "numeric",
      month: "long", day: "numeric",
    });
  }
  return null;
}

function alertPopup(f) {
  var p = f.properties;
  var html = "<h3>" + (esc(p.title) || "Trail alert") + "</h3>" +
    kvTable([
      ["Date", alertDateText(p)],
      ["Location", p.location],
    ]);
  if (p.description) {
    html += "<p class='alert-desc'>" + esc(p.description) + "</p>";
  }
  html += "<p class='pop-note'><em>Trail alert from the North " +
    "Country Trail Association.</em></p>";
  return html;
}

/* Chapter places (the chapter's own place records —
   data/points/chapter-places.geojson, seeded from the NCTA
   camping points and hand-maintained since; emitted to the site
   by scripts/build_chapter_places.py). One card serves both the
   layer's own features and the gazetteer twins (whose record
   provenance rides in place_source instead of source), so the
   layer, Find and What's here can never disagree. A chapter
   entry SUPERSEDES its NCTA point: the gazetteer build drops the
   NCTA version and the Places layer skips chapter entries, so a
   place shows exactly once — as its chapter version. */
/* Directions (Paul, Nov 10, 2026 — "so we can share the
   trailheads and navigate there by driving"): every point card
   — gazetteer points and chapter places — offers a Google Maps
   driving link. The destination is the point's OWN coordinates
   at 6 dp, plain signed decimals, never the place name: names
   can mis-geocode in rural areas, and the pin must land on the
   real spot. The name rides only in the card the link sits in. */
function directionsHtml(f) {
  var c = f.geometry && f.geometry.coordinates;
  if (!c) return "";
  return "<a class='pop-directions' target='_blank' rel='noopener' " +
    "href='https://www.google.com/maps/dir/?api=1&destination=" +
    c[1].toFixed(6) + "," + c[0].toFixed(6) +
    "'>Driving directions</a>";
}

function chapterPopupHtml(f) {
  var p = f.properties;
  var source = p.source != null && p.source !== "chapter"
    ? p.source : p.place_source;
  var seeded = !!source && source.indexOf("seeded from NCTA") === 0;
  var closed = p.status === "closed";
  var html = "<h3>" + (esc(p.name) || "Chapter place") + "</h3>";
  if (closed) html += "<p class='chapter-closed'>CLOSED</p>";
  var rows = [
    ["Kind", p.kind],
    ["Status", !closed && p.status
      ? p.status.charAt(0).toUpperCase() + p.status.slice(1) : null],
    ["Capacity", p.capacity],
    ["Water", p.water_note],
    ["Chapter tracker mile",
      p.nct_mile != null ? p.nct_mile : null],
    ["From the west end",
      p.from_west_mi != null ? p.from_west_mi + " mi along the trail" : null],
  ];
  if (p.off_chain) {
    rows.push(["Position", "Off the depicted chapter chain — nearest " +
      "depicted point ≈ " + (p.snap_m / 1000).toFixed(1) + " km"]);
  }
  html += kvTable(rows);
  if (p.description) {
    html += "<p class='chapter-desc'>" + esc(p.description) + "</p>";
  }
  var actions = "";
  if (p.section && walkByName[p.section]) {
    actions += "<button type='button' class='pop-door' data-section='" +
      esc(p.section) + "'>Open " + esc(p.section) + " record</button>";
  }
  actions += directionsHtml(f);
  if (actions) html += "<div class='pop-actions'>" + actions + "</div>";
  html += seeded
    ? "<p class='pop-note'><em>Seeded from NCTA data — chapter " +
      "record to be confirmed.</em></p>"
    : "<p class='pop-note'><em>Chapter record — Itasca Moraine " +
      "Chapter.</em></p>";
  return html;
}

function accessPopup(f) {
  var p = f.properties;
  var s = ACCESS_STYLES[p.source_type];
  var html = "<h3>" + (esc(p.name) || (s ? s.label : "Access line")) + "</h3>" +
    kvTable([
      ["Kind", s ? s.label : p.source_type],
      ["Length", p.miles ? p.miles + " mi" : null],
      ["Source", p.dataset],
    ]);
  if (p.cut) html += "<p class='pop-note'>Continues beyond the corridor</p>";
  if (p.connector) {
    html += "<p class='pop-note'>Kept whole — a connector that " +
      "crosses the trail</p>";
  }
  return html;
}

function roadPopup(f) {
  var p = f.properties;
  var s = ROAD_CLASS_STYLES[p.road_class];
  var html = "<h3>" + (esc(p.name) || (s ? s.label : "Road")) + "</h3>" +
    kvTable([
      ["Class", s ? s.label : p.road_class],
      ["Source", p.dataset],
    ]);
  if (p.cut) html += "<p class='pop-note'>Continues beyond the corridor</p>";
  if (p.connector) {
    html += "<p class='pop-note'>Kept whole — a connector that " +
      "crosses the trail</p>";
  }
  return html;
}

/* Type codes to display names (registry data/assets/registry.json).
   Shared by the popup title and the hover chip. */
var ASSET_TYPE_NAMES = {
  BN: "Bench", BR: "Bridge", BW: "Boardwalk", CP: "Carsonite post",
  CS: "Campsite", KI: "Kiosk", LT: "Latrine", PK: "Parking area",
  PO: "Post", RG: "Register", SG: "Sign", SH: "Shelter",
  UN: "Unclassified", WT: "Water source",
};
function assetTypeName(code) {
  if (!code) return "Asset";
  return ASSET_TYPE_NAMES[String(code).toUpperCase()] ||
    (String(code).charAt(0).toUpperCase() + String(code).slice(1));
}
/* Per-type asset toggles (Paul, Nov 12, 2026): the Asset pins
   toggle grows eleven sub-toggles, one per type, with the pin
   count each carries. Counts verified against
   data/assets.geojson (84 pins total); UN covers both "UN"
   and "unclassified" (17 + 1 = 18). Order is the brief's
   order — largest first. */
var ASSET_TYPE_TOGGLES = [
  ["CP", 30], ["SG", 16], ["BW", 10], ["BN", 3], ["BR", 2],
  ["CS", 1], ["LT", 1], ["KI", 1], ["PO", 1], ["RG", 1], ["UN", 18],
];
var assetTypeOn = {};
ASSET_TYPE_TOGGLES.forEach(function (t) { assetTypeOn[t[0]] = true; });
var assetsTypeLayers = {};
function assetTypeCode(f) {
  var t = (f.properties || {}).type;
  if (!t) return "UN";
  t = String(t).toUpperCase();
  if (t === "UNCLASSIFIED") return "UN";
  return t;
}

/* Condition in plain language (R5): the pin's grade is a word
   plus what it means for the crew — "worn" alone tells a
   volunteer nothing. */
var CONDITION_GLOSS = {
  "new": "New — sound and readable",
  worn: "Worn — readable, aging, watch it",
  replace: "Replace — not doing its job",
  good: "Good — sound",
  fair: "Fair — sound, weathered",
  poor: "Poor — failing",
};
function fmtPhotoDate(dt) {
  /* EXIF "2026:11:11 10:54:23" → "Nov 11, 2026". */
  var m = /^(\d{4}):(\d{2}):(\d{2})/.exec(dt || "");
  if (!m) return dt || null;
  var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return months[+m[2] - 1] + " " + (+m[3]) + ", " + m[1];
}

function assetPopup(f) {
  var p = f.properties || {};
  var typeName = assetTypeName(p.type);
  var unidentified = !p.type || p.type.toUpperCase() === "UN" ||
    p.type.toLowerCase() === "unclassified";
  var html;
  if (unidentified) {
    /* R5: a pin we cannot name says so — never a guessed
       type. The note (what the classifier could see) is the
       description; the walk-through is the next step. */
    html = "<h3>Not yet identified</h3>" +
      "<p class='pop-sub'>Needs a walk-through — we don't know " +
      "what this is yet.</p>";
  } else {
    html = "<h3>" + esc(typeName) + "</h3>";
    if (p.serial) {
      html += "<p class='pop-sub'>" + esc(p.serial) +
        (p.section ? " · " + esc(p.section) : "") +
        (p.chainage_mi != null ? " · mi " + p.chainage_mi : "") +
        "</p>";
    }
  }
  /* Every photo of the item, not just the primary: the inventory
     collapses duplicate photos onto one pin (Nov 11, 2026), and
     the extra photos live in p.photos. Pins without a photos
     array (unclassified, fresh from the pipeline) fall back to
     the single derivative. */
  var photos = (p.photos && p.photos.length) ? p.photos :
    (p.derivative ? [{ derivative: p.derivative }] : []);
  if (photos.length === 1 && photos[0].derivative) {
    html += "<img src=\"assets-photos/" + esc(photos[0].derivative) +
      "\" alt=\"\" style=\"max-width:100%;display:block;margin:6px 0 2px\">";
    /* Photo date under the photo (Paul, Nov 12): the date the
       photo was taken, from its EXIF datetime. */
    var d1 = fmtPhotoDate(photos[0].datetime || p.datetime);
    if (d1) html += "<div class=\"pop-photo-date\">" + esc(d1) + "</div>";
  } else if (photos.length > 1) {
    /* Face flip (Nov 11, 2026): one face at a time — Front/Back for
       two photos, Face 1/2/3… for more — with a "Show all photos"
       that opens the full grid, so no photo is hidden. The compass
       bearing is NOT shown: the phone records no camera direction
       (direction_deg is null on every Nov 11 photo), so the faces
       are labelled by the order they were shot; if a future batch
       carries per-photo direction_deg, append it to the label here. */
    var faceLabel = function (i) {
      return photos.length === 2 ? (i === 0 ? "Front" : "Back")
        : "Face " + (i + 1);
    };
    /* Face label carries the photo's date too (Paul, Nov 12):
       "Front · Nov 11, 2026". Each photo's own EXIF datetime. */
    var faceDate = function (i) {
      return fmtPhotoDate((photos[i] && photos[i].datetime) || p.datetime);
    };
    var faceLabelDate = function (i) {
      var d = faceDate(i);
      return faceLabel(i) + (d ? " · " + d : "");
    };
    html += "<div class=\"pop-flip\">";
    html += "<img class=\"pop-face-img\" src=\"assets-photos/" +
      esc(photos[0].derivative) +
      "\" alt=\"\" style=\"max-width:100%;display:block;margin:6px 0 2px\">";
    html += "<div class=\"pop-face-label\">" + esc(faceLabelDate(0)) + "</div>";
    html += "<div class=\"pop-face-btns\">";
    photos.forEach(function (ph, i) {
      if (!ph.derivative) return;
      html += "<button type=\"button\" class=\"pop-face" +
        (i === 0 ? " active" : "") + "\" data-derivative=\"" +
        esc(ph.derivative) + "\" data-label=\"" + esc(faceLabel(i)) +
        "\" data-date=\"" + esc(faceDate(i) || "") +
        "\">" + esc(faceLabel(i)) + "</button>";
    });
    html += "<button type=\"button\" class=\"pop-faces-all\">" +
      "Show all photos</button>";
    html += "</div>";
    html += "<div class=\"pop-face-grid\">";
    photos.forEach(function (ph) {
      if (ph.derivative) {
        html += "<img src=\"assets-photos/" + esc(ph.derivative) +
          "\" alt=\"\">";
      }
    });
    html += "</div></div>";
  }
  var rows = [];
  if (unidentified) {
    rows.push(["Section", p.section]);
    if (p.note) rows.push(["What we can see", p.note]);
  } else {
    rows.push(["Condition", p.condition ?
      (CONDITION_GLOSS[p.condition] || p.condition) : null]);
  }
  rows.push(["Photographed", fmtPhotoDate(p.datetime)]);
  rows.push(["Photographer", p.photographer]);
  rows.push(["Source", "Itasca Moraine Chapter — volunteer photo inventory"]);
  if (photos.length > 1) rows.push(["Photos", photos.length + " photos"]);
  /* Classify link (Paul, Nov 12): the pin opens the
     classification interface at this pin, so the chapter can
     jump from the map to classifying it. Serial is the key;
     unclassified pins link to the interface's Needs
     classification view. */
  var classifyHref = "classify.html" +
    (p.serial ? "#pin=" + encodeURIComponent(p.serial) : "");
  html += "<p class='pop-classify'><a href='" + classifyHref +
    "' target='_blank' rel='noopener'>Classify this pin</a></p>";
  return html + kvTable(rows);
}

/* §2.11: an asset pin whose photo was condition-graded wears a
   ring in the grade colour (good green / fair amber / poor red;
   Carsonite posts use Paul's Nov 11 functional scheme instead —
   new green / worn amber / replace red) around the pin disc.
   Ungraded pins keep the plain disc. */
var CONDITION_RINGS = { good: "#1a9850", fair: "#e08214",
                        poor: "#b2182b",
                        "new": "#1a9850", worn: "#e08214",
                        replace: "#b2182b" };

/* Pictographic asset pins (Paul, Nov 12, 2026): one glyph per
   type, white on the orange pin disc, so a volunteer reads what
   a pin IS at a glance. Every type in ASSET_TYPE_NAMES has a
   glyph, even the ones with no pins today (PK, SH, WT). Glyphs
   are 16x16 inline SVG, simple and bold for legibility at pin
   size. The cutouts (tent door, outhouse door, sign/register
   lines) use the disc colour #e6550d — keep in step with
   COLORS.assetPin. */
var ASSET_GLYPHS = {
  CP: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<rect x=\"5\" y=\"1.5\" width=\"6\" height=\"4\" rx=\"0.8\" fill=\"#fff\"/>" +
    "<rect x=\"7\" y=\"5\" width=\"2\" height=\"9\" fill=\"#fff\"/></svg>",
  SG: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<rect x=\"2\" y=\"2\" width=\"12\" height=\"6\" rx=\"1\" fill=\"#fff\"/>" +
    "<rect x=\"4\" y=\"4\" width=\"8\" height=\"1.2\" fill=\"#e6550d\"/>" +
    "<rect x=\"7\" y=\"8\" width=\"2\" height=\"6\" fill=\"#fff\"/></svg>",
  BW: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<rect x=\"2\" y=\"2.5\" width=\"12\" height=\"2.6\" rx=\"0.6\" fill=\"#fff\"/>" +
    "<rect x=\"2\" y=\"6.7\" width=\"12\" height=\"2.6\" rx=\"0.6\" fill=\"#fff\"/>" +
    "<rect x=\"2\" y=\"10.9\" width=\"12\" height=\"2.6\" rx=\"0.6\" fill=\"#fff\"/></svg>",
  BN: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<rect x=\"2\" y=\"2\" width=\"12\" height=\"2.2\" rx=\"0.6\" fill=\"#fff\"/>" +
    "<rect x=\"2\" y=\"6.5\" width=\"12\" height=\"2.2\" rx=\"0.6\" fill=\"#fff\"/>" +
    "<rect x=\"3.5\" y=\"8.7\" width=\"1.8\" height=\"5\" fill=\"#fff\"/>" +
    "<rect x=\"10.7\" y=\"8.7\" width=\"1.8\" height=\"5\" fill=\"#fff\"/></svg>",
  BR: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<path d=\"M2 13 Q8 3 14 13\" fill=\"none\" stroke=\"#fff\" " +
    "stroke-width=\"2\" stroke-linecap=\"round\"/>" +
    "<rect x=\"1\" y=\"13\" width=\"14\" height=\"1.6\" fill=\"#fff\"/></svg>",
  CS: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<path d=\"M8 2 L14.5 13 L1.5 13 Z\" fill=\"#fff\"/>" +
    "<path d=\"M8 7.5 L10.5 13 L5.5 13 Z\" fill=\"#e6550d\"/></svg>",
  KI: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<path d=\"M1.5 6.5 L8 1.5 L14.5 6.5 Z\" fill=\"#fff\"/>" +
    "<rect x=\"4\" y=\"7\" width=\"8\" height=\"4.5\" rx=\"0.5\" fill=\"#fff\"/>" +
    "<rect x=\"4.8\" y=\"11.5\" width=\"1.6\" height=\"2.5\" fill=\"#fff\"/>" +
    "<rect x=\"9.6\" y=\"11.5\" width=\"1.6\" height=\"2.5\" fill=\"#fff\"/></svg>",
  LT: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<path d=\"M2.5 6.5 L8 1.5 L13.5 6.5 Z\" fill=\"#fff\"/>" +
    "<rect x=\"4\" y=\"6.5\" width=\"8\" height=\"7\" fill=\"#fff\"/>" +
    "<rect x=\"7\" y=\"9\" width=\"2\" height=\"4.5\" fill=\"#e6550d\"/></svg>",
  PO: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<rect x=\"6\" y=\"1.5\" width=\"4\" height=\"1.8\" rx=\"0.6\" fill=\"#fff\"/>" +
    "<rect x=\"7\" y=\"3\" width=\"2\" height=\"11\" fill=\"#fff\"/></svg>",
  RG: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<rect x=\"3.5\" y=\"1.5\" width=\"9\" height=\"6\" rx=\"1\" fill=\"#fff\"/>" +
    "<rect x=\"5.5\" y=\"3.5\" width=\"5\" height=\"1.2\" fill=\"#e6550d\"/>" +
    "<rect x=\"7\" y=\"7.5\" width=\"2\" height=\"6.5\" fill=\"#fff\"/></svg>",
  UN: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<text x=\"8\" y=\"12.5\" text-anchor=\"middle\" font-size=\"12\" " +
    "font-weight=\"800\" fill=\"#fff\" font-family=\"sans-serif\">?</text></svg>",
  PK: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<text x=\"8\" y=\"12.5\" text-anchor=\"middle\" font-size=\"12\" " +
    "font-weight=\"800\" fill=\"#fff\" font-family=\"sans-serif\">P</text></svg>",
  SH: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<path d=\"M1.5 8 L8 2 L14.5 8 Z\" fill=\"#fff\"/>" +
    "<rect x=\"3\" y=\"8.5\" width=\"1.8\" height=\"5.5\" fill=\"#fff\"/>" +
    "<rect x=\"11.2\" y=\"8.5\" width=\"1.8\" height=\"5.5\" fill=\"#fff\"/></svg>",
  WT: "<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\">" +
    "<path d=\"M8 1.5 C8 1.5 3.5 7 3.5 9.8 A4.5 4.5 0 0 0 12.5 9.8 " +
    "C12.5 7 8 1.5 8 1.5 Z\" fill=\"#fff\"/></svg>",
};
function assetMarker(f, latlng) {
  var glyph = ASSET_GLYPHS[assetTypeCode(f)] || ASSET_GLYPHS.UN;
  var ring = CONDITION_RINGS[(f.properties || {}).condition];
  var inner = "<span class='asset-pin'>" + glyph + "</span>";
  var html = ring ?
    "<span class='asset-pin-ringed' style='background:" + ring +
    "'>" + inner + "</span>" : inner;
  return L.marker(latlng, {
    keyboard: false,
    icon: L.divIcon({
      className: "asset-pin-wrap", iconSize: [26, 26],
      iconAnchor: [13, 13], html: html,
    }),
  });
}

/* Spiderfy (Paul, Nov 12, 2026): asset pins 1–3 m apart stack
   their glyphs, so the one underneath is unclickable. Clicking
   a stack fans its pins out on a circle (~36 px) with a thin
   leg from the anchor to each fanned pin; a second click on a
   fanned pin opens its popup. Plain Leaflet, no plugin — the
   pins are L.marker (divIcon), so setLatLng moves the whole
   icon. State lives here and is fully cleared on unspiderfy.
   The stack test is screen-pixel based (~20 px at the current
   zoom), so it works at any zoom; at the zooms where pins are
   read (Z3/Z4) 20 px is roughly the 1–10 m the stacks span. */
var SPIDERFY_PX = 20;
var SPIDERFY_RADIUS = 36;
var assetPins = [];        /* {layer, feature, latlng} — every asset pin */
var assetTypeBoxes = {};   /* type code -> its panel checkbox */
var spiderfyState = null;  /* {pins, legs, anchor} while fanned */
var spiderfyPinClick = false; /* a pin handled this click; the map
   click that follows in the same dispatch must not unspiderfy */

function spiderfyStackFor(layer) {
  var origin = null, i;
  for (i = 0; i < assetPins.length; i++) {
    if (assetPins[i].layer === layer) { origin = assetPins[i]; break; }
  }
  if (!origin) return [];
  var def = layerById("assets");
  var group = def && def.layer;
  if (!group) return [origin];
  var centre = map.latLngToContainerPoint(origin.latlng);
  var stack = [];
  for (i = 0; i < assetPins.length; i++) {
    var p = assetPins[i];
    var sub = assetsTypeLayers[assetTypeCode(p.feature)];
    if (!sub || !group.hasLayer(sub)) continue; /* type toggled off */
    var pt = map.latLngToContainerPoint(p.latlng);
    var dx = pt.x - centre.x, dy = pt.y - centre.y;
    if (Math.sqrt(dx * dx + dy * dy) <= SPIDERFY_PX) stack.push(p);
  }
  return stack;
}

function spiderfy(stack, clickedLayer) {
  var anchor = null, i;
  for (i = 0; i < stack.length; i++) {
    if (stack[i].layer === clickedLayer) { anchor = stack[i].latlng; break; }
  }
  if (!anchor) anchor = stack[0].latlng;
  var centre = map.latLngToContainerPoint(anchor);
  var legs = L.layerGroup();
  var n = stack.length;
  for (i = 0; i < n; i++) {
    var angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    var pt = L.point(
      centre.x + SPIDERFY_RADIUS * Math.cos(angle),
      centre.y + SPIDERFY_RADIUS * Math.sin(angle));
    var ll = map.containerPointToLatLng(pt);
    stack[i].layer.setLatLng(ll);
    legs.addLayer(L.polyline([anchor, ll], {
      color: "#555", weight: 1.5, opacity: 0.8, interactive: false,
    }));
  }
  legs.addTo(map);
  spiderfyState = { pins: stack, legs: legs, anchor: anchor };
}

function unspiderfy() {
  if (!spiderfyState) return;
  spiderfyState.pins.forEach(function (p) {
    p.layer.setLatLng(p.latlng); /* back to the EXACT original spot */
  });
  if (spiderfyState.legs) map.removeLayer(spiderfyState.legs);
  spiderfyState = null;
}

function onAssetPinClick(l, f) {
  spiderfyPinClick = true;
  window.setTimeout(function () { spiderfyPinClick = false; }, 0);
  if (spiderfyState) {
    var inFan = false;
    spiderfyState.pins.forEach(function (p) {
      if (p.layer === l) inFan = true;
    });
    if (inFan) { l.openPopup(); return; } /* second click: ITS popup */
    unspiderfy(); /* a different stack: collapse the old fan first */
  }
  var stack = spiderfyStackFor(l);
  if (stack.length <= 1) { l.openPopup(); return; }
  spiderfy(stack, l); /* first click fans out — no popup yet */
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

/* (The Access points layer was removed Nov 10, 2026 — Paul: "isn't
   great. Let's get rid of it." The computed crossings live on in the
   gazetteer as its Road/Trail crossing entries; the access-points
   data file and its builder remain in the repo.) */

/* Where a section's name label sits (v6, Paul, Nov 10, 2026):
   the label must NEVER touch the line. v3–v5 judged only the
   segment direction at the length-centroid and offset by a fixed
   few px, so on curving sections the name still landed on the
   tread (West-5, 8a, 9, 11, 13, 14, 16). The rule now, for every
   section: consider eight candidate boxes around the anchor —
   the anchor is the point on the LINE nearest the section's
   vertex-centroid — and pick the first box, in house preference
   order, whose rectangle clears every vertex of the section's
   own polyline by LABEL_CLEARANCE px. Candidates walk outward
   (17, 26, 34 px standoff) before any fallback; the fallback
   (anchor at an extreme bend) takes the least-bad box, pushed to
   44 px. Deterministic: same data, same placement, every load.
   The standoffs walked up a step with the labels themselves in
   v8 (Paul, Nov 10, 2026 evening — names at 14 px / 700): the
   boxes the pass measures are bigger, so the first candidate
   starts further out to preserve the same clearance. */
var LABEL_CLEARANCE = 4;
function sectionLabelPlacement(f, name, mapRef) {
  var coords = (f.geometry && f.geometry.coordinates) || [];
  var fallback = { direction: "top", offset: [0, -17] };
  if (coords.length < 2 || !mapRef) return fallback;
  /* Anchor: nearest point on the polyline to the vertex centroid
     (keeps the anchor ON the line and near the visual middle,
     unlike the bbox centre, which can sit off-line in a bend). */
  var cx = 0, cy = 0;
  coords.forEach(function (c) { cx += c[0]; cy += c[1]; });
  cx /= coords.length; cy /= coords.length;
  var anchor = null, bestD = Infinity;
  for (var i = 1; i < coords.length; i++) {
    var ax = coords[i - 1][0], ay = coords[i - 1][1];
    var bx = coords[i][0], by = coords[i][1];
    var dx = bx - ax, dy = by - ay;
    var len2 = dx * dx + dy * dy;
    var t = len2 ? ((cx - ax) * dx + (cy - ay) * dy) / len2 : 0;
    t = Math.max(0, Math.min(1, t));
    var px = ax + t * dx, py = ay + t * dy;
    var d = (cx - px) * (cx - px) + (cy - py) * (cy - py);
    if (d < bestD) { bestD = d; anchor = [px, py]; }
  }
  if (!anchor) return fallback;
  var apt = mapRef.latLngToContainerPoint(
    L.latLng(anchor[1], anchor[0]));
  /* The section's own line, in container px at the current zoom. */
  var linePts = coords.map(function (c) {
    return mapRef.latLngToContainerPoint(L.latLng(c[1], c[0]));
  });
  var font = 14;
  var w = (name || "").length * font * 0.62 + 8, h = font + 7;
  function boxFor(dir, dist) {
    var x = apt.x, y = apt.y;
    if (dir === "top") y -= dist + h;
    else if (dir === "bottom") y += dist;
    else if (dir === "left") { x -= dist + w; y -= h / 2; }
    else if (dir === "right") { x += dist; y -= h / 2; }
    else if (dir === "topright") { x += dist * 0.7; y -= dist * 0.7 + h; }
    else if (dir === "topleft") { x -= dist * 0.7 + w; y -= dist * 0.7 + h; }
    else if (dir === "bottomright") { x += dist * 0.7; y += dist * 0.7; }
    else if (dir === "bottomleft") { x -= dist * 0.7 + w; y += dist * 0.7; }
    return { x0: x, y0: y, x1: x + w, y1: y + h };
  }
  function clearance(box) {
    var worst = Infinity;
    linePts.forEach(function (p) {
      var dx = Math.max(box.x0 - p.x, 0, p.x - box.x1);
      var dy = Math.max(box.y0 - p.y, 0, p.y - box.y1);
      var d = Math.sqrt(dx * dx + dy * dy);
      if (d < worst) worst = d;
    });
    return worst;
  }
  var dirs = ["top", "right", "bottom", "left",
    "topright", "topleft", "bottomright", "bottomleft"];
  var dists = [17, 26, 34];
  var best = null;
  for (var di = 0; di < dists.length; di++) {
    for (var dj = 0; dj < dirs.length; dj++) {
      var box = boxFor(dirs[dj], dists[di]);
      var cl = clearance(box);
      if (!best || cl > best.cl) {
        best = { dir: dirs[dj], dist: dists[di], cl: cl, box: box };
      }
      if (cl >= LABEL_CLEARANCE) {
        return {
          direction: dirs[dj], offset: [0, 0], anchor: anchor,
          box: box, apt: { x: apt.x, y: apt.y }, w: w, h: h,
        };
      }
    }
  }
  /* Extreme bend: least-bad box, pushed further out. */
  var fb = boxFor(best.dir, 44);
  return {
    direction: best.dir, offset: [0, 0], anchor: anchor,
    box: fb, apt: { x: apt.x, y: apt.y }, w: w, h: h,
  };
}

/* Leaflet tooltip direction + pixel offset that centres the
   label box chosen by sectionLabelPlacement. Tooltip offsets
   position the tooltip's TIP, so convert the wanted box
   position back into a direction/offset pair. */
function tooltipForBox(place) {
  var dx = place.box.x0 + place.w / 2 - place.apt.x;
  var dyTop = place.box.y1 - place.apt.y;   /* box bottom edge */
  var dyBot = place.box.y0 - place.apt.y;   /* box top edge */
  if (place.dir === "top") {
    return { direction: "top", offset: [dx, dyTop] };
  }
  if (place.dir === "bottom") {
    return { direction: "bottom", offset: [dx, dyBot] };
  }
  if (place.dir === "left" || place.dir === "right") {
    var dy = place.box.y0 + place.h / 2 - place.apt.y;
    var edge = place.dir === "left" ? place.box.x1 : place.box.x0;
    return { direction: place.dir, offset: [edge - place.apt.x, dy] };
  }
  /* Diagonals ride the nearest cardinal direction. */
  if ((place.dir || "").indexOf("top") === 0) {
    return { direction: "top", offset: [dx, dyTop] };
  }
  return { direction: "bottom", offset: [dx, dyBot] };
}

/* Screen-space rect of a rendered label element (for the
   label-vs-label collision pass). */
function labelRectOf(el, layer) {
  var r = el.getBoundingClientRect();
  var mr = map.getContainer().getBoundingClientRect();
  return {
    x0: r.left - mr.left, y0: r.top - mr.top,
    x1: r.right - mr.left, y1: r.bottom - mr.top,
  };
}

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
   there are only two, at opposite ends of the chapter.
   v4 refinements (UX P8 + DESIGN §3): the collision box is offset
   by the label's direction (side labels extend right of their
   anchor, not around it), the estimated width carries +6 px of
   slop, no name ever hides at z ≥ 12, and at z ≤ 9 only sections
   ≥ 2 mi keep names. */
var sectionLabelItems = [];
var mileLabelItems = [];   /* mile-marker tooltips (M2) */
var chainageItems = [];    /* S1 numerals: {marker, latlng, miles, every10} */
var chainageGroupRef = null;

function _boxesCollide(a, b) {
  return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
}

/* §2.7 unified annotation pass (v7): ONE collision pool for every
   text class on the map face, reserved in the fixed priority
   order — terminus (never hides) > gap > section > mile/chainage.
   The v6 guarantee is preserved exactly: every section label
   first receives a placement that provably clears its OWN line
   (pass 1, sectionLabelPlacement), and in pass 2 a label either
   shows at that placement or hides — nothing of any class is ever
   shoved onto a line to resolve a collision. Lower classes test
   an estimated box (the house +6 px slop method) against the pool
   and yield. */
function layoutAnnotations() {
  var z = map.getZoom();
  var font = z >= 12 ? 14 : z === 11 ? 13 : z === 10 ? 12 : 11;
  var placed = [];
  /* Priority 0 — termini reserve their real boxes, never hide. */
  document.querySelectorAll(".terminus-label span").forEach(
    function (el) { placed.push(labelRectOf(el)); });
  /* §2.5: the tick bars keep priority over labels — a name that
     would touch a tick hides before a tick moves. The test uses
     the ticks' PLACED boxes at the current zoom (their current
     endpoints, fattened by the bar's weight), never a fixed
     radius — the v4 fixed-radius version of this rule hid every
     name at z10 and was removed; this is the precise form the
     cartography spec asks for. Section ticks reserve only when
     they render (z > 8); terminus ticks always render. */
  function reserveTick(it, halfWeight) {
    var ll = it.casing.getLatLngs();
    if (!ll || ll.length < 2) return;
    var a = map.latLngToContainerPoint(ll[0]);
    var b = map.latLngToContainerPoint(ll[1]);
    placed.push({
      x0: Math.min(a.x, b.x) - halfWeight,
      y0: Math.min(a.y, b.y) - halfWeight,
      x1: Math.max(a.x, b.x) + halfWeight,
      y1: Math.max(a.y, b.y) + halfWeight,
    });
  }
  terminusTickItems.forEach(function (it) { reserveTick(it, 5); });
  if (z > 8) {
    boundaryTickItems.forEach(function (it) { reserveTick(it, 3); });
  }
  /* Priority 1 — the gap label, when it is on the map. */
  gapLabelMarkers.forEach(function (m) {
    if (!gapLabelGroupRef || !gapLabelGroupRef.hasLayer(m)) return;
    var el = m.getElement && m.getElement();
    var span = el && el.querySelector("span");
    if (span) placed.push(labelRectOf(span));
  });
  var sorted = sectionLabelItems.slice().sort(function (a, b) {
    return (b.len || 0) - (a.len || 0);
  });
  /* Pass 1: every label gets a placement that provably clears its
     OWN line at this zoom (the never-touch rule), whether or not
     it ends up shown. */
  sorted.forEach(function (it) {
    var tt = it.layer.getTooltip();
    if (!tt) return;
    var place = sectionLabelPlacement(it.feature, it.name, map);
    if (!place.anchor) return;
    it.place = place;
    var tip = tooltipForBox(place);
    tt.options.direction = tip.direction;
    tt.options.offset = L.point(tip.offset);
    tt.setLatLng(L.latLng(place.anchor[1], place.anchor[0]));
  });
  /* Pass 2: greedy label-vs-label deconfliction in the section's
     length order, measured on the REAL rendered boxes (Leaflet
     has now positioned them per pass 1): a label that would
     overlap an already-placed one is hidden at this zoom, never
     shoved onto a line. Shown labels reserve their box in the
     shared pool at every zoom, so the lower classes can yield. */
  sorted.forEach(function (it) {
    var tt = it.layer.getTooltip();
    var el = tt && tt.getElement();
    if (!el) return;
    el.style.fontSize = font + "px";
    var show = true;
    if (z <= 9 && (it.len || 0) < 2) show = false;
    var r = labelRectOf(el);
    if (show && z < 13) {
      if (placed.some(function (p) { return _boxesCollide(r, p); })) {
        show = false;
      }
    }
    if (show) placed.push(r);
    el.style.display = show ? "" : "none";
  });
  /* Priority 3a — S1 chainage numerals (10-mile points; the
     5-mile points ride the layer for print only, CSS-hidden on
     screen): slate numerals ON the line at Z2+, yielding to
     everything above. */
  if (chainageGroupRef) {
    chainageItems.forEach(function (it) {
      if (!it.every10) return;
      var want = z >= 11;
      if (want) {
        var pt = map.latLngToContainerPoint(it.latlng);
        var w = String(it.miles).length * 9.5 * 0.62 + 8, h = 16;
        var box = { x0: pt.x - w / 2, y0: pt.y - h / 2,
                    x1: pt.x + w / 2, y1: pt.y + h / 2 };
        if (placed.some(function (p) { return _boxesCollide(box, p); })) {
          want = false;
        } else {
          placed.push(box);
        }
      }
      if (want && !chainageGroupRef.hasLayer(it.marker)) {
        chainageGroupRef.addLayer(it.marker);
      }
      if (!want && chainageGroupRef.hasLayer(it.marker)) {
        chainageGroupRef.removeLayer(it.marker);
      }
    });
  }
  /* Priority 3b — M2 mile labels: whole-mile numbers at Z3+,
     half-mile numbers at Z4 only, both at the pool's mercy. */
  mileLabelItems.forEach(function (it) {
    var tt = it.layer.getTooltip();
    var el = tt && tt.getElement();
    if (!el) return;
    var want = it.isHalf ? z >= 15 : z >= 13;
    if (want) {
      var pt = map.latLngToContainerPoint(it.latlng);
      var w = String(it.num).length * 9.5 * 0.62 + 6, h = 15;
      var box = { x0: pt.x - w / 2, y0: pt.y - 6 - h,
                  x1: pt.x + w / 2, y1: pt.y - 6 };
      if (placed.some(function (p) { return _boxesCollide(box, p); })) {
        want = false;
      } else {
        placed.push(box);
      }
    }
    el.style.display = want ? "" : "none";
  });
  var tFont = z >= 11 ? 12 : z === 10 ? 11 : 10;
  document.querySelectorAll(".terminus-label span").forEach(
    function (el) { el.style.fontSize = tFont + "px"; });
}
map.on("zoomend moveend", layoutAnnotations);

/* The gap's on-map name (DESIGN D4) shows at z ≥ 9 only. Markers
   live in the gaps layer's own label group (gapLabelGroupRef, set
   by the gaps build), so they follow the gaps toggle. */
var gapLabelMarkers = [];
function layoutGapLabels() {
  if (!gapLabelGroupRef) return;
  var z = map.getZoom();
  var show = z >= 9;
  /* S2: at Z2+ the gap's name becomes a Carsonite-style sign chip
     (the brown post-mounted marker idiom of the trail itself);
     below Z2 it stays the bare haloed label it has been. */
  document.body.classList.toggle("gap-chip", z >= 11);
  gapLabelMarkers.forEach(function (m) {
    if (show && !gapLabelGroupRef.hasLayer(m)) {
      gapLabelGroupRef.addLayer(m);
    }
    if (!show && gapLabelGroupRef.hasLayer(m)) {
      gapLabelGroupRef.removeLayer(m);
    }
  });
}
map.on("zoomend", layoutGapLabels);

/* S2 breathing gap: while the gaps layer is on, the tab is
   visible, motion is allowed and we are not printing, the core's
   dash pattern marches westward — one full dash period (14+8 px)
   per ~6 s. The gap geometry runs west→east on the file, so a
   growing dashOffset moves the pattern toward its start: west.
   Static (offset 0) in print via the beforeprint hook below. */
var REDUCED_MOTION = !!(window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches);
var gapMarchRaf = null;
function gapMarchShouldRun() {
  return !printMode && !REDUCED_MOTION && !document.hidden &&
    !!gapCoreLayer && !!gapsGroupRef && map.hasLayer(gapsGroupRef);
}
function gapMarchTick(ts) {
  if (!gapMarchShouldRun()) { gapMarchRaf = null; return; }
  var off = ((ts % 6000) / 6000) * 22;
  gapCoreLayer.setStyle({ dashOffset: String(off) });
  gapMarchRaf = window.requestAnimationFrame(gapMarchTick);
}
function updateGapMarch() {
  if (gapMarchShouldRun() && gapMarchRaf === null) {
    gapMarchRaf = window.requestAnimationFrame(gapMarchTick);
  }
}
document.addEventListener("visibilitychange", updateGapMarch);
map.on("layeradd layerremove", function (e) {
  if (e.layer === gapsGroupRef) updateGapMarch();
});

/* S5 print hooks: Leaflet canvas paths can't be restyled from
   print CSS, so the print collapse (roads to classes A+F in one
   grey; access to solid hairlines, winter snowmobile kept) is
   applied by restyling the layers for the print render and
   restored afterwards. The gap march freezes at offset 0. */
function restyleContextLayers() {
  if (accessLayerRef) accessLayerRef.setStyle(accessStyle);
  if (roadsGroupRef) {
    roadsGroupRef.eachLayer(function (l) { l.setStyle(roadStyle); });
  }
}
window.addEventListener("beforeprint", function () {
  printMode = true;
  if (gapCoreLayer) gapCoreLayer.setStyle({ dashOffset: "0" });
  restyleContextLayers();
});
window.addEventListener("afterprint", function () {
  printMode = false;
  restyleContextLayers();
  updateGapMarch();
});

/* ------------------------------------------------- selection model
   One selection state for sections + the gap (UX-REVIEW Part 1).
   Entry points: click/tap a section or gap line, Find, the
   inspector's Prev/Next buttons, and ←/→ while the inspector has
   focus. Selecting renders the record into the panel inspector and
   draws a persistent casing highlight on the map; pan/zoom change
   nothing. Clicking empty map (or the official line) clears. */
var walkItems = [];          /* sections + gap, sorted by chainage */
var walkByName = {};
var gapWalkItem = null;
var selection = null;        /* the selected walk item, or null */
var selectionHalo = null;    /* L.layerGroup on the map, or null */
var suppressMapClear = false;

function registerWalkItem(item) {
  walkItems.push(item);
  walkItems.sort(function (a, b) { return a.chainage - b.chainage; });
  walkByName[item.name] = item;
  if (item.type === "gap") gapWalkItem = item;
}

function featureLatLngs(f) {
  var g = f.geometry || {};
  var lines = g.type === "MultiLineString" ? g.coordinates
    : g.type === "LineString" ? [g.coordinates] : [];
  return lines.map(function (line) {
    return line.map(function (c) { return L.latLng(c[1], c[0]); });
  });
}

function gazSectionRecord(name) {
  if (!gazFeatures) return null;
  for (var i = 0; i < gazFeatures.length; i++) {
    var f = gazFeatures[i];
    if (f.properties.kind === "Section" && f.properties.name === name) {
      return f.properties;
    }
  }
  return null;
}

/* Merged record for the inspector: gazetteer (tracker) fields win;
   the stretch feature's own fields fill gaps and stand alone until
   the index loads. */
function sectionRecord(item) {
  var sp = item.feature.properties || {};
  var gz = gazSectionRecord(item.name) || {};
  function pick(key) { return gz[key] != null ? gz[key] : sp[key]; }
  return {
    name: item.name,
    tracker_section: pick("tracker_section"),
    length_mi: pick("length_mi"),
    tracker_length_mi: pick("tracker_length_mi"),
    has_adopter: pick("has_adopter"),
    adopter_display: pick("adopter_display"),
    sawyer_display: gz.sawyer_display || null,
    description: gz.description || null,
    map_refs: gz.map_refs || null,
    ncta_sheets: gz.ncta_sheets || sp.ncta_sheets || null,
    nct_mile: gz.nct_mile != null ? gz.nct_mile : null,
    nct_mile_start: gz.nct_mile_start != null ? gz.nct_mile_start : null,
    nct_mile_end: gz.nct_mile_end != null ? gz.nct_mile_end : null,
    from_west_mi: gz.from_west_mi != null ? gz.from_west_mi : null,
    from_east_mi: gz.from_east_mi != null ? gz.from_east_mi : null,
    help_requested: gz.help_requested != null ? gz.help_requested : null,
    maintenance_2026: gz.maintenance_2026 || null,
    land_context: gz.land_context || null,
    comments: gz.comments || null,
    comments_dropped: !!gz.comments_dropped,
    access_at_start: sp.access_at_start,
    access_at_end: sp.access_at_end,
    both_ends_access: sp.both_ends_access,
  };
}

function fmtMi(v) { return v != null ? v + " mi" : null; }

function drawSelectionHalo(item) {
  clearSelectionHalo();
  var parts = featureLatLngs(item.feature);
  if (!parts.length) return;
  var layers = [];
  parts.forEach(function (ll) {
    layers.push(L.polyline(ll, { renderer: canvasFor(),
      interactive: false, color: "#ffffff", weight: 10, opacity: 0.9 }));
  });
  /* §2.13: the halo core is the selected element's OWN style at
     weight + 2 — the same colour and dash it already wears, never
     a foreign highlight. */
  parts.forEach(function (ll) {
    if (item.type === "gap") {
      layers.push(L.polyline(ll, { renderer: canvasFor(),
        interactive: false, color: COLORS.gap,
        weight: GAP_CORE_STYLE.weight + 2, opacity: 1,
        dashArray: GAP_CORE_STYLE.dashArray }));
    } else {
      layers.push(L.polyline(ll, { renderer: canvasFor(),
        interactive: false, color: COLORS.adopted,
        weight: stretchStyle().weight + 2, opacity: 1 }));
    }
  });
  selectionHalo = L.layerGroup(layers).addTo(map);
}

function clearSelectionHalo() {
  if (selectionHalo) { map.removeLayer(selectionHalo); selectionHalo = null; }
}

function setLabelActive(name, on) {
  sectionLabelItems.forEach(function (it) {
    if (it.name !== name) return;
    var tt = it.layer.getTooltip();
    var el = tt && tt.getElement();
    if (el) el.classList.toggle("label-active", !!on);
  });
}

function selectSection(item, source) {
  if (!item) return;
  closeChip();
  if (selection) setLabelActive(selection.name, false);
  selection = item;
  drawSelectionHalo(item);
  if (item.type === "section") setLabelActive(item.name, true);
  renderInspector();
  var el = document.getElementById("inspector");
  if (el) el.scrollIntoView({ block: "nearest" });
  /* The full record rides the gazetteer index; re-render when it
     lands so a first click isn't stuck with the stretch subset. */
  if (!gazFeatures) gazLoad(function () {
    if (selection === item) renderInspector();
  });
}

function clearSelection() {
  if (selection) setLabelActive(selection.name, false);
  selection = null;
  clearSelectionHalo();
  renderInspector();
}

function selectStep(delta) {
  if (!walkItems.length) return;
  var idx = selection ? walkItems.indexOf(selection) : -1;
  var next = idx < 0
    ? (delta > 0 ? 0 : walkItems.length - 1)
    : idx + delta;
  if (next < 0 || next >= walkItems.length) return;
  selectSection(walkItems[next], "prevnext");
}

function zoomToSelection() {
  if (!selection) return;
  var parts = featureLatLngs(selection.feature);
  if (!parts.length) return;
  var bounds = null;
  parts.forEach(function (ll) {
    var b = L.latLngBounds(ll);
    bounds = bounds ? bounds.extend(b) : b;
  });
  if (bounds) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
}

map.on("click", function () {
  if (spiderfyPinClick) return; /* a pin handled this click */
  unspiderfy(); /* clicking empty map collapses a fan */
  if (suppressMapClear) return;
  if (selection) clearSelection();
});
/* Spiderfy teardown: the fan is pixel-derived, so a zoom makes
   it stale; closing the popup ends the fan's job; removing the
   assets layer must not strand its legs on the map. */
map.on("zoomstart", unspiderfy);
map.on("popupclose", function () { unspiderfy(); });
map.on("layerremove", function (e) {
  var def = layerById("assets");
  if (def && def.layer && e.layer === def.layer) unspiderfy();
});
/* Shareable view: every pan or zoom writes the new view into the
   hash, so the address bar always matches what is on screen. */
map.on("moveend", writeShareHash);
document.addEventListener("keydown", function (e) {
  if (e.key !== "Escape") return;
  var input = document.getElementById("gaz-search");
  if (document.activeElement === input) return;
  if (selection) clearSelection();
});

/* ------------------------------------------------------- inspector */

function inspRow(k, v) {
  var val = esc(v);
  if (val === null) return "";
  return "<div class='insp-row'><span class='k'>" + k +
    "</span><span>" + val + "</span></div>";
}

/* Story-box ask (design-notes §2.4): the gap annotation + line in
   the panel header select the gap, same as the inspector callout. */
(function wireGapStory() {
  var btn = document.getElementById("gap-story");
  if (btn) btn.addEventListener("click", function () {
    if (gapWalkItem) selectSection(gapWalkItem, "inspector");
  });
})();

/* S5 Winter mode: a panel toggle for snowmobile season — the
   snowmobile lines gain weight on screen, and (via printMode in
   accessStyle) survive the print collapse. */
(function wireWinter() {
  var box = document.getElementById("winter-toggle");
  if (!box) return;
  box.addEventListener("change", function () {
    winterMode = box.checked;
    document.body.classList.toggle("winter", winterMode);
    if (accessLayerRef) accessLayerRef.setStyle(accessStyle);
  });
})();

function renderInspector() {
  var el = document.getElementById("inspector");
  if (!el) return;
  el.classList.toggle("has-selection", !!selection);
  if (!selection) {
    el.innerHTML =
      "<div class='insp-empty'>Select a section: click the amber " +
      "line, or find it above — or pick a job from the list above. " +
      "← → walk the trail.</div>";
    return;
  }
  el.innerHTML = selection.type === "gap"
    ? gapInspectorHtml(selection)
    : sectionInspectorHtml(selection);
  wireInspector();
}

/* The action row (pop-up spec §1.2): directly under the header
   band, replacing the old footer. Five actions, in meeting order —
   walk, frame, share. Zoom is the row's one primary button. */
function inspectorActions(idx, isGap) {
  var prevDis = idx <= 0 ? " disabled" : "";
  var nextDis = idx < 0 || idx >= walkItems.length - 1 ? " disabled" : "";
  return "<div class='insp-actions'>" +
    "<span class='insp-walk'>" +
    "<button type='button' id='insp-prev'" + prevDis + ">‹ Prev</button>" +
    "<button type='button' id='insp-next'" + nextDis + ">Next ›</button>" +
    "</span>" +
    "<button type='button' class='primary' id='insp-zoom'>" +
    (isGap ? "Zoom to the gap" : "Zoom to section") + "</button>" +
    "<button type='button' id='insp-copy'>" +
    (isGap ? "Copy the story" : "Copy brief") + "</button>" +
    "<button type='button' id='insp-print'>Print</button>" +
    "</div>";
}

function inspProv() {
  return "<div class='insp-prov'>From the chapter adoption tracker.</div>";
}

/* Position line (§4): chainage from each end, each half omitted
   when its value is absent, no line when both are. */
function positionLine(r) {
  var bits = [];
  if (r.from_west_mi != null) {
    bits.push(r.from_west_mi + " mi from the west end");
  }
  if (r.from_east_mi != null) {
    bits.push(r.from_east_mi + " mi from the east end");
  }
  if (!bits.length) return "";
  return "<p class='insp-caption'>" + esc(bits.join(" · ")) + "</p>";
}

/* Getting in (§1.4): the crew leader's first question as a named
   block. Sections carry boolean end access only, and the copy says
   exactly that much; the gap carries its named gapEndAccess()
   strings verbatim. */
function accessStripHtml(startVal, endVal, oneEndOnly) {
  var html = "<div class='insp-block insp-access-wrap'>" +
    "<div class='insp-block-label'>Getting in</div>" +
    "<div class='insp-access'>" +
    "<div class='acc-cell'><div class='acc-end'>West end</div>" +
    "<div class='acc-val'>" + esc(startVal) + "</div></div>" +
    "<div class='acc-cell'><div class='acc-end'>East end</div>" +
    "<div class='acc-val'>" + esc(endVal) + "</div></div>" +
    "</div>";
  if (oneEndOnly) {
    html += "<p class='acc-note'>Access at one end only.</p>";
  }
  return html + "</div>";
}

function endAccessText(b) {
  if (b == null) return "No crossing recorded";
  return b ? "Crossing recorded" : "No crossing recorded";
}

/* What's here (§1.6): out of the fold, always visible when the
   section has contents, kinds in action order, at most 8 names
   per kind, and every name a button that runs the gazSelect()
   path — the same jump choosing it in Find performs. */
var CONTENTS_KIND_ORDER = ["Parking", "Road crossing", "Trail crossing",
  "Camping", "Water", "Shelter", "POI", "Section boundary",
  "Chapter end"];
function contentsHtml(sectionName) {
  if (!gazFeatures) return "";
  var contents = gazContents(sectionName);
  var kinds = CONTENTS_KIND_ORDER.filter(function (k) {
    return contents[k] && contents[k].length;
  });
  Object.keys(contents).forEach(function (k) {
    if (kinds.indexOf(k) < 0 && contents[k].length) kinds.push(k);
  });
  if (!kinds.length) return "";
  var html = "<div class='insp-block gaz-contents'>" +
    "<div class='insp-block-label'>What's here</div>";
  kinds.forEach(function (k) {
    var feats = contents[k];
    var shown = feats.slice(0, 8);
    html += "<div class='gc-row'><span class='gc-kind'>" + esc(k) +
      " (" + feats.length + ")</span><span class='gc-names'>";
    shown.forEach(function (f, i) {
      if (i) html += " · ";
      html += "<button type='button' class='gc-name' " +
        "data-gaz='" + esc(f.properties.name) + "'>" +
        esc(f.properties.name) + "</button>";
    });
    if (feats.length > shown.length) {
      html += " and " + (feats.length - shown.length) + " more";
    }
    html += "</span></div>";
  });
  return html + "</div>";
}

function lengthText(r) {
  var t = r.length_mi != null ? r.length_mi + " mi" : null;
  if (t && r.tracker_length_mi != null &&
      r.tracker_length_mi !== r.length_mi) {
    t += " (tracker " + r.tracker_length_mi + ")";
  }
  return t;
}

/* Copy brief (§1.3): plain text from the record's real fields
   only; a line whose fields are empty is omitted, never padded. */
function sectionBrief(r) {
  var lines = [];
  var head = r.name + (r.tracker_section
    ? " (" + r.tracker_section + ")" : "") + " — Itasca Moraine Chapter";
  lines.push(head);
  var bits = [];
  var len = lengthText(r);
  if (len) bits.push("Length " + len);
  if (r.nct_mile_start != null && r.nct_mile_end != null) {
    bits.push("Chapter tracker miles " + r.nct_mile_start + "–" +
      r.nct_mile_end);
  }
  if (r.from_west_mi != null) {
    bits.push(r.from_west_mi + " mi from the west end");
  }
  if (bits.length) lines.push(bits.join(" · "));
  var crew = [];
  if (r.adopter_display && r.adopter_display.length) {
    crew.push("Adopted by " + r.adopter_display.join(", "));
  }
  if (r.sawyer_display && r.sawyer_display.length) {
    crew.push("Sawyer " + r.sawyer_display.join(", "));
  }
  if (crew.length) lines.push(crew.join(" · "));
  if (r.help_requested != null && r.help_requested !== "") {
    lines.push("Help requested: " + String(r.help_requested));
  }
  if (r.access_at_start != null || r.access_at_end != null) {
    lines.push("Access: crossing " +
      (r.access_at_start ? "recorded" : "not recorded") +
      " at the west end; crossing " +
      (r.access_at_end ? "recorded" : "not recorded") +
      " at the east end.");
  }
  if (gazFeatures) {
    var contents = gazContents(r.name);
    var kinds = CONTENTS_KIND_ORDER.filter(function (k) {
      return contents[k] && contents[k].length;
    });
    Object.keys(contents).forEach(function (k) {
      if (kinds.indexOf(k) < 0 && contents[k].length) kinds.push(k);
    });
    if (kinds.length) {
      lines.push("What's here: " + kinds.map(function (k) {
        return k + " (" + contents[k].length + ")";
      }).join(", "));
    }
  }
  if (r.description) { lines.push(""); lines.push(r.description); }
  lines.push("");
  lines.push("From the chapter trail map.");
  return lines.join("\n");
}

/* Copy the story (§2): the gap's brief — the recruiting text,
   assembled from the gap feature's real fields, ending on the
   header spec's ask, verbatim. */
function gapBrief(p) {
  var lines = [];
  lines.push("The chapter's one unadopted stretch: " + p.gap_id +
    " — " + p.length_mi + " mi at the west end");
  lines.push("of the Itasca Moraine Chapter line, in " +
    p.land_context + ".");
  lines.push("");
  lines.push("West end: " + gapEndAccess(p, "start"));
  lines.push("East end: " + gapEndAccess(p, "end"));
  var crossings = (p.crossings || []).map(function (c) {
    return c.label + (c.dist_mi != null ? " (" + c.dist_mi + " mi in)" : "");
  });
  if (crossings.length) {
    lines.push("Trails crossing it: " + crossings.join("; "));
  }
  lines.push("");
  lines.push("It needs an adopter.");
  return lines.join("\n");
}

/* One shared copy routine (§1.2): clipboard first; on failure the
   brief lands in a temporary selected textarea for manual copy —
   never a silent no-op. The button reads "Copied" for two
   seconds, then reverts. */
function copyBriefText(text, btn) {
  function done() {
    if (!btn) return;
    var orig = btn.getAttribute("data-label") || btn.textContent;
    btn.setAttribute("data-label", orig);
    btn.textContent = "Copied";
    window.setTimeout(function () { btn.textContent = orig; }, 2000);
  }
  function fallback() {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "8px";
    ta.style.bottom = "8px";
    ta.style.zIndex = "3000";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    window.setTimeout(function () { ta.remove(); }, 8000);
    done();
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, fallback);
  } else {
    fallback();
  }
}

/* NCTA map-sheet line (Phase 3, Nov 11, 2026): the section's
   official sheet(s) in the NCTA Minnesota map series, computed by
   line-vs-sheet-frame intersection (scripts live in
   working/ncta-sheets/; the mapping rides the section records as
   ncta_sheets). Each sheet id links the series PDF at the sheet's
   own page — in the 3/16/2026 edition PDF page N is sheet MN-0NN.
   The printed mile ranges are the NCTA reckoning from the sheets
   themselves, never the chapter tracker miles. */
var NCTA_SHEET_PDF = "https://northcountrytrail.org/maps/mn_map_series.pdf";
var NCTA_SHEET_MILES = {
  "MN-023": "MN-121\u2013127", "MN-024": "MN-127\u2013133",
  "MN-025": "MN-134\u2013140", "MN-026": "MN-140\u2013146",
  "MN-027": "MN-146\u2013152", "MN-028": "MN-152\u2013157",
  "MN-029": "MN-157\u2013162", "MN-030": "MN-162\u2013167",
  "MN-031": "MN-168\u2013172", "MN-032": "MN-172\u2013176",
  "MN-033": "MN-177\u2013183", "MN-034": "MN-183\u2013189",
  "MN-035": "MN-189\u2013195", "MN-036": "MN-195\u2013202",
  "MN-037": "MN-198\u2013204", "MN-038": "MN-205\u2013210",
  "MN-039": "MN-210\u2013216", "MN-040": "MN-217\u2013223",
  "MN-041": "MN-224\u2013229", "MN-042": "MN-230\u2013234",
  "MN-043": "MN-234\u2013239", "MN-044": "MN-239\u2013246",
};
function nctaSheetLine(ids) {
  if (!ids || !ids.length) return "";
  var links = ids.map(function (sid) {
    var page = parseInt(sid.slice(3), 10);
    var miles = NCTA_SHEET_MILES[sid];
    return "<a href='" + NCTA_SHEET_PDF + "#page=" + page +
      "' target='_blank' rel='noopener'>" + esc(sid) + "</a>" +
      (miles ? " <span class='muted'>(" + miles + ")</span>" : "");
  });
  return "<p class='insp-crew'>Official NCTA sheet" +
    (ids.length > 1 ? "s" : "") + ": " + links.join(", ") +
    " <span class='muted'>(PDF)</span></p>";
}

function sectionInspectorHtml(item) {
  var r = sectionRecord(item);
  var idx = walkItems.indexOf(item);
  var adopted = !!r.has_adopter;
  var html = "<div class='insp-sheet'>";
  html += "<div class='insp-head'><span class='insp-title'>" +
    (esc(r.name) || "Section") + "</span>";
  if (r.tracker_section) {
    html += "<span class='insp-code'>" + esc(r.tracker_section) + "</span>";
  }
  /* Adopted wears the soft green tint (§1.1) — it is the normal,
     good state; red stays the colour of exception, spent once. */
  html += "<span class='insp-pill " +
    (adopted ? "adopted soft" : "unadopted") +
    "'>" + (adopted ? "Adopted" : "Not adopted") + "</span>";
  html += "<button type='button' class='insp-close' id='insp-close' " +
    "aria-label='Clear selection'>×</button></div>";
  html += inspectorActions(idx, false);
  html += "<div class='insp-body'>";
  html += positionLine(r);
  /* Key strip (§1.1/§3): three cells — Length, Chapter tracker
     miles, Adopted by. Sawyer and map refs ride the crew line. */
  var ks = "";
  var len = lengthText(r);
  if (len) {
    var lenHtml = esc(len);
    if (r.tracker_length_mi != null &&
        r.tracker_length_mi !== r.length_mi) {
      lenHtml = esc(r.length_mi + " mi") +
        " <span class='muted'>(tracker " + r.tracker_length_mi +
        ")</span>";
    }
    ks += "<div><div class='ks-label'>Length</div>" +
      "<div class='ks-value'>" + lenHtml + "</div></div>";
  }
  if (r.nct_mile_start != null && r.nct_mile_end != null) {
    ks += "<div><div class='ks-label'>Chapter tracker miles</div>" +
      "<div class='ks-value'>" + r.nct_mile_start + "–" +
      r.nct_mile_end + "</div></div>";
  }
  if (r.adopter_display && r.adopter_display.length) {
    ks += "<div><div class='ks-label'>Adopted by</div>" +
      "<div class='ks-value'>" +
      esc(r.adopter_display.join(", ")) + "</div></div>";
  }
  if (ks) html += "<div class='insp-keystrip'>" + ks + "</div>";
  var crew = "";
  if (r.sawyer_display && r.sawyer_display.length) {
    crew = "Sawyer: <span class='crew-names'>" +
      esc(r.sawyer_display.join(", ")) + "</span>";
  }
  if (r.map_refs && r.map_refs.length) {
    crew += (crew ? " · " : "") + "Map " +
      esc(r.map_refs.join(", "));
  }
  if (crew) html += "<p class='insp-crew'>" + crew + "</p>";
  html += nctaSheetLine(r.ncta_sheets);
  /* Ask band (§1.5): the tracker value verbatim, red spent on the
     label only, one honest action — the same Copy brief. */
  if (r.help_requested != null && r.help_requested !== "") {
    var hv = String(r.help_requested);
    var sentence = /[a-z]/i.test(hv) && hv.trim().indexOf(" ") >= 0;
    html += "<div class='insp-ask'><div class='ask-label'>" +
      "Help requested</div><div class='ask-value" +
      (sentence ? " prose" : "") + "'>" + esc(hv) + "</div>" +
      "<button type='button' class='ask-copy' id='insp-ask-copy'>" +
      "Copy a brief for the crew</button></div>";
  }
  html += accessStripHtml(endAccessText(r.access_at_start),
    endAccessText(r.access_at_end), r.both_ends_access === false);
  if (r.description) {
    var long = String(r.description).length > 160;
    html += "<p class='insp-desc" + (long ? " clamped" : "") +
      "' id='insp-desc'>" + esc(r.description) + "</p>";
    if (long) {
      html += "<button type='button' class='insp-more' " +
        "id='insp-more'>More</button>";
    }
  }
  html += contentsHtml(item.name);
  /* Record details (§3): only what the hierarchy demotes here. */
  var rows = "";
  rows += inspRow("Land", r.land_context);
  rows += inspRow("2026 maintenance", r.maintenance_2026);
  if (r.comments) rows += inspRow("Tracker comments", r.comments);
  else if (r.comments_dropped) {
    rows += inspRow("Tracker comments",
      "Withheld from the public map");
  }
  if (rows) {
    html += "<details class='insp-details'><summary>Record " +
      "details</summary><div class='insp-rows'>" + rows +
      "</div></details>";
  }
  html += printNoteHtml();
  html += "</div>" + inspProv() + "</div>";
  return html;
}

/* R7: the Winter print note — the old standalone Winter
   checkbox is gone (Winter is a Background choice now); when
   the Winter background is active, the handout says so. */
function printNoteHtml() {
  var note = "Maintenance notes and tracker comments are in the " +
    "chapter adoption tracker.";
  if (winterMode) {
    note += " Snowmobile trails are shown — winter background.";
  }
  return "<p class='insp-print-note'>" + note + "</p>";
}

function gapInspectorHtml(item) {
  var p = item.feature.properties || {};
  var gz = gazSectionRecord(p.gap_id) || {};
  var idx = walkItems.indexOf(item);
  var html = "<div class='insp-sheet is-gap'>";
  html += "<div class='insp-head'><span class='insp-title'>" +
    (esc(p.gap_id) || "Gap") + "</span>" +
    "<span class='insp-pill unadopted'>Not adopted</span>" +
    "<button type='button' class='insp-close' id='insp-close' " +
    "aria-label='Clear selection'>×</button></div>";
  html += inspectorActions(idx, true);
  html += "<div class='insp-body'>";
  html += "<div class='insp-standing'><strong>No adopter — this is " +
    "the chapter's recruiting gap.</strong></div>" +
    "<p class='insp-ask-print'>It needs an adopter.</p>";
  html += positionLine(gz);
  var ks = "";
  if (p.length_mi != null) {
    ks += "<div><div class='ks-label'>Length</div>" +
      "<div class='ks-value'>" + p.length_mi + " mi</div></div>";
  }
  if (p.land_context) {
    ks += "<div><div class='ks-label'>Land</div>" +
      "<div class='ks-value'>" + esc(p.land_context) + "</div></div>";
  }
  if (ks) html += "<div class='insp-keystrip'>" + ks + "</div>";
  html += nctaSheetLine(p.ncta_sheets);
  /* Getting in — named, because the gap's data is named (§2). */
  html += accessStripHtml(gapEndAccess(p, "start"),
    gapEndAccess(p, "end"), false);
  if (p.name) html += "<p class='insp-desc'>" + esc(p.name) + "</p>";
  html += contentsHtml(p.gap_id);
  var rows = "";
  rows += inspRow("Type",
    p.trail_stat === "off-road" ? "Off-road trail" : p.trail_stat);
  rows += inspRow("Note", p.note);
  if (rows) {
    html += "<details class='insp-details'><summary>Gap " +
      "details</summary><div class='insp-rows'>" + rows +
      "</div></details>";
  }
  html += printNoteHtml();
  html += "</div>" + inspProv() + "</div>";
  return html;
}

function currentBrief() {
  if (!selection) return "";
  if (selection.type === "gap") {
    return gapBrief(selection.feature.properties || {});
  }
  return sectionBrief(sectionRecord(selection));
}

function wireInspector() {
  var close = document.getElementById("insp-close");
  if (close) close.addEventListener("click", clearSelection);
  var zoom = document.getElementById("insp-zoom");
  if (zoom) zoom.addEventListener("click", zoomToSelection);
  var prev = document.getElementById("insp-prev");
  if (prev) prev.addEventListener("click", function () { selectStep(-1); });
  var next = document.getElementById("insp-next");
  if (next) next.addEventListener("click", function () { selectStep(1); });
  var copy = document.getElementById("insp-copy");
  if (copy) copy.addEventListener("click", function () {
    copyBriefText(currentBrief(), copy);
  });
  var askCopy = document.getElementById("insp-ask-copy");
  if (askCopy) askCopy.addEventListener("click", function () {
    copyBriefText(currentBrief(), askCopy);
  });
  var print = document.getElementById("insp-print");
  if (print) print.addEventListener("click", function () {
    window.print();
  });
  var more = document.getElementById("insp-more");
  if (more) more.addEventListener("click", function () {
    var d = document.getElementById("insp-desc");
    if (!d) return;
    var clamped = d.classList.toggle("clamped");
    more.textContent = clamped ? "More" : "Less";
  });
  /* What's-here name buttons: the gazSelect() path, exactly what
     choosing the feature in Find performs (§1.6). The section
     selection is untouched. */
  var names = document.querySelectorAll("#inspector .gc-name");
  names.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var f = gazFeatureByName(btn.getAttribute("data-gaz"));
      if (f) gazSelect(f);
    });
  });
}

/* ←/→ walk the trail while the inspector (or a control inside it)
   has focus; the Find input keeps its own arrow behaviour because
   focus is in the panel's other subtree there. */
(function inspectorKeys() {
  var el = document.getElementById("inspector");
  if (!el) return;
  el.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") { e.preventDefault(); selectStep(-1); }
    if (e.key === "ArrowRight") { e.preventDefault(); selectStep(1); }
    if (e.key === "Escape") { clearSelection(); }
  });
})();

/* ----------------------------------------------------- hover chip
   Hover chip (Nov 11 redesign — docs/design-notes-2026-11-11-
   hover-chip.md): a 300 ms dwell raises a small static chip that
   IDENTIFIES and TRIAGES — head row (display name + status pill),
   identity line, one facts row of nowrap tokens. Facts and status
   come from the stretch feature's own properties, fixed at hover
   time; the tracker description and the help FLAG (never its
   value) ride the gazetteer merge the inspector uses, read once
   at arm time. It never follows the cursor, carries no action,
   and stays pointer-events:none. Touch (coarse pointer) never
   sees it. */
var chipTimer = null;
var chipTip = null;
var chipLayer = null;

/* Facts tokens for the section/gap chip: an array of short
   strings, each rendered nowrap — length, chainage span (the
   map's own ruler, one decimal), the official NCTA sheet(s),
   and the section's last-work note (the sanitized 2026
   maintenance note build_gazetteer.py stamps onto the stretch
   feature). Any token whose fields are absent is omitted.
   Stretch properties only. The access verdict left the chip on
   Paul's order (Nov 11, 2026); access still lives on the click
   record, and the access properties stay in the data. */
function chipSheetToken(p) {
  var s = p.ncta_sheets;
  if (!s || !s.length) return null;
  return (s.length === 1 ? "Sheet " : "Sheets ") + s.join(" + ");
}

/* The last-work note rides as ONE nowrap token, so a long note
   is cut at a word boundary past CHIP_NOTE_MAX chars, with an
   ellipsis; trailing glue (a dangling "Test" from a cut
   "Test adopter N", "&", small words, punctuation) is trimmed
   so the cut never strands a fragment. The full note stays on
   the click record. */
var CHIP_NOTE_MAX = 40;
function chipNoteToken(p) {
  var n = p.maintenance_2026;
  if (!n) return null;
  n = String(n).trim();
  if (!n) return null;
  if (n.length <= CHIP_NOTE_MAX) return n;
  var cut = n.slice(0, CHIP_NOTE_MAX);
  var sp = cut.lastIndexOf(" ");
  if (sp > 0) cut = cut.slice(0, sp);
  cut = cut.replace(/(\s+(Test|&|and|the|a))+$/, "");
  cut = cut.replace(/[\s;:,.-]+$/, "");
  if (!cut) cut = n.slice(0, CHIP_NOTE_MAX);
  return cut + "…";
}

function chipFactTokens(p, isGap) {
  var toks = [];
  if (p.length_mi != null) toks.push(p.length_mi + " mi");
  if (isGap) {
    toks.push("the chapter's recruiting gap");
    var gSheet = chipSheetToken(p);
    if (gSheet) toks.push(gSheet);
    return toks;
  }
  if (p.chainage_start_mi != null && p.chainage_end_mi != null) {
    toks.push("mi " + p.chainage_start_mi.toFixed(1) + "–" +
      p.chainage_end_mi.toFixed(1));
  }
  var sheet = chipSheetToken(p);
  if (sheet) toks.push(sheet);
  var note = chipNoteToken(p);
  if (note) toks.push(note);
  return toks;
}

function chipFactsHtml(toks) {
  if (!toks.length) return "";
  return "<span class='hc-facts'>" + toks.map(function (t) {
    return "<span class='hc-fact'>" + esc(t) + "</span>";
  }).join(" · ") + "</span>";
}

/* Status pill for the chip's head row — same vocabulary and
   colours as the inspector's .insp-pill (shared .status-pill
   base in style.css). Help outranks adopted: a section that is
   held AND asking shows the ask. */
function chipPillHtml(help, adopted, isGap) {
  if (isGap) {
    return "<span class='status-pill unadopted'>Not adopted</span>";
  }
  if (help) return "<span class='status-pill help'>Help requested</span>";
  if (adopted) {
    return "<span class='status-pill adopted soft'>Adopted</span>";
  }
  return "<span class='status-pill unadopted'>Not adopted</span>";
}

function armChip(layer, feature, latlng, place) {
  if (COARSE_POINTER) return;
  disarmChip();
  if (layer.setStyle && layer._walkItem &&
      layer._walkItem.type === "section") {
    layer.setStyle(STRETCH_HOVER_STYLE);
  }
  chipLayer = layer;
  chipTimer = window.setTimeout(function () {
    chipTimer = null;
    var p = feature.properties || {};
    var isGap = !p.tracker_section && !!p.gap_id;
    var title = isGap ? (p.gap_id || "Gap") : (p.name || "Section");
    var sub = null, pill;
    if (isGap) {
      sub = p.land_context || null;
      pill = chipPillHtml(false, false, true);
    } else {
      /* Description + help flag via the inspector's merge, read
         once, now. Before the gazetteer loads both are absent and
         the chip simply shows less — never anything false. */
      var rec = layer._walkItem ? sectionRecord(layer._walkItem) : {};
      sub = rec.description || null;
      var help = rec.help_requested != null &&
        rec.help_requested !== "";
      pill = chipPillHtml(help, !!p.has_adopter, false);
    }
    var html = "<span class='hc-head'><span class='hc-name'>" +
      (esc(title) || "") + "</span>" + pill + "</span>";
    if (sub) html += "<span class='hc-sub'>" + esc(sub) + "</span>";
    html += chipFactsHtml(chipFactTokens(p, isGap));
    chipTip = L.tooltip({
      direction: place.direction, offset: place.offset,
      className: "hover-chip", opacity: 1,
    }).setLatLng(latlng).setContent(html);
    map.openTooltip(chipTip);
  }, 300);
}

function disarmChip() {
  if (chipTimer) { window.clearTimeout(chipTimer); chipTimer = null; }
  if (chipLayer && chipLayer.setStyle && chipLayer._walkItem &&
      chipLayer._walkItem.type === "section") {
    chipLayer.setStyle(stretchStyle());
  }
  chipLayer = null;
}

function closeChip() {
  disarmChip();
  if (chipTip) { map.closeTooltip(chipTip); chipTip = null; }
}
map.on("movestart zoomstart", closeChip);

/* §2.13: the context lines (roads, non-road access) get the same
   300 ms dwell chip as the sections — name + class, plus the
   corridor note for clipped features — because at hairline
   weights the popups are hard to discover. Same machinery, same
   rules: static chip, never follows the cursor, no chips on
   coarse pointers. */
function armContextChip(layer, feature, latlng, kind) {
  if (COARSE_POINTER) return;
  disarmChip();
  chipLayer = layer;
  chipTimer = window.setTimeout(function () {
    chipTimer = null;
    var p = feature.properties || {};
    var title, klass;
    if (kind === "road") {
      var rs = ROAD_CLASS_STYLES[p.road_class];
      title = p.name || (rs ? rs.label : "Road");
      klass = rs ? rs.label : null;
    } else {
      var as = ACCESS_STYLES[p.source_type];
      title = p.name || (as ? as.label : "Access line");
      klass = as ? as.label : null;
    }
    var bits = [];
    if (klass && klass !== title) bits.push(klass);
    if (p.cut) bits.push("continues beyond the corridor");
    if (p.connector) bits.push("connector — kept whole");
    /* Content unchanged (Nov 10 §7 ruled it right); only the
       Nov 11 geometry applies — head-row name, token facts, and
       the hint line is gone with the section chip's. */
    var html = "<span class='hc-head'><span class='hc-name'>" +
      (esc(title) || "") + "</span></span>";
    html += chipFactsHtml(bits);
    chipTip = L.tooltip({
      direction: "top", offset: [0, -8],
      className: "hover-chip", opacity: 1,
    }).setLatLng(latlng).setContent(html);
    map.openTooltip(chipTip);
  }, 300);
}

function wireContextHover(l, f, kind) {
  l.on("mouseover", function (e) {
    armContextChip(l, f, e.latlng, kind);
  });
  l.on("mouseout", closeChip);
}

/* §2.14: asset pins get the same 300 ms dwell chip as the
   sections and context lines (Paul, Nov 11, 2026 — "not seeing
   bubbles when I mouse over the points"): serial + type in the
   head row, condition / section / chainage / photo count as
   facts. Same machinery, same rules: static chip, never follows
   the cursor, no chips on coarse pointers. The chip binds to the
   pin's interactive child layer(s) — a graded pin is a
   layerGroup whose rings are interactive:false, so the mouseover
   is wired on every child and only the dot fires. */
function armAssetChip(layer, feature, latlng) {
  if (COARSE_POINTER) return;
  disarmChip();
  chipLayer = layer;
  chipTimer = window.setTimeout(function () {
    chipTimer = null;
    var p = feature.properties || {};
    var title = p.serial ? p.serial + " — " + assetTypeName(p.type)
                         : assetTypeName(p.type);
    var bits = [];
    if (p.condition) {
      bits.push(p.condition.charAt(0).toUpperCase() +
        p.condition.slice(1) + " condition");
    }
    if (p.section) bits.push(p.section);
    if (p.chainage_mi != null) bits.push("mi " + p.chainage_mi);
    var n = (p.photos && p.photos.length) || 0;
    if (n > 1) bits.push(n + " photos");
    var html = "<span class='hc-head'><span class='hc-name'>" +
      esc(title) + "</span></span>";
    html += chipFactsHtml(bits);
    chipTip = L.tooltip({
      direction: "top", offset: [0, -8],
      className: "hover-chip", opacity: 1,
    }).setLatLng(latlng).setContent(html);
    map.openTooltip(chipTip);
  }, 300);
}

function wireAssetHover(l, f) {
  if (COARSE_POINTER) return;
  var layers = l.getLayers ? l.getLayers() : [l];
  layers.forEach(function (child) {
    child.on("mouseover", function (e) {
      armAssetChip(l, f, e.latlng);
    });
    child.on("mouseout", closeChip);
  });
}

/* ------------------------------------------------------------ layers */
/* Each layer: file under data/, builder, default-on flag, panel
   group (Chapter / Context), and the swatch its toggle wears —
   legend swatches are generated from these same style constants
   (DESIGN Larger Move 7: hand-copied legend strings drifted in v3;
   generated ones cannot). Files are fetched lazily on first
   enable. `missingOk` layers (assets) quietly show empty when
   their file is absent. */

function swatchFor(def) {
  var s = def.swatch;
  if (!s) return "";
  if (s.kind === "bar") {
    return "<span class='tog-swatch-bar' style='background:" +
      s.color + "'></span>";
  }
  if (s.kind === "pin") {
    return "<span class='tog-swatch-pin' style='background:" +
      s.color + "'></span>";
  }
  if (s.kind === "fill") {
    return "<span class='tog-swatch-fill' style='background:" +
      s.color + ";border-color:" + (s.border || s.color) +
      "'></span>";
  }
  if (s.kind === "alert") {
    return "<span class='tog-swatch-alert' style='background:" +
      s.color + "'></span>";
  }
  if (s.kind === "chapter") {
    return "<span class='tog-swatch-chapter' style='background:" +
      s.color + "'></span>";
  }
  return "<span class='tog-swatch-line" + (s.dashed ? " dashed" : "") +
    "' style='border-top-color:" + s.color + "'></span>";
}

var gapLabelGroupRef = null;

/* Canopy height hover readout (Paul, Nov 12, 2026): hovering
   the Tree height overlay reads the height in metres under the
   cursor. The canopy-height tiles colour each pixel by the same
   ramp the tile builder uses (scripts/build_lidar_trio.py
   RAMP_STOPS: white 0–1 m, greens deepening to 25 m), so the
   readout samples the tile pixel and inverts the ramp. Tiles
   are same-origin, so canvas readback is allowed. A
   transparent pixel means outside the corridor (no data). */
var CANOPY_RAMP = [  /* (height m, [r, g, b]) — mirrors RAMP_STOPS */
  [0, [255, 255, 255]], [1, [255, 255, 255]],
  [2, [215, 238, 200]], [5, [180, 220, 165]],
  [9, [140, 200, 120]], [14, [100, 175, 90]],
  [19, [64, 145, 72]], [20, [34, 110, 55]],
  [25, [12, 64, 30]],
];
var canopyLut = null;
function canopyLutBuild() {
  if (canopyLut) return canopyLut;
  canopyLut = [];
  for (var i = 0; i <= 256; i++) {
    var h = i * 25 / 256;
    var c = CANOPY_RAMP[CANOPY_RAMP.length - 1][1];
    for (var j = 0; j < CANOPY_RAMP.length - 1; j++) {
      var h0 = CANOPY_RAMP[j][0], h1 = CANOPY_RAMP[j + 1][0];
      if (h >= h0 && h <= h1) {
        var t = h1 === h0 ? 0 : (h - h0) / (h1 - h0);
        var c0 = CANOPY_RAMP[j][1], c1 = CANOPY_RAMP[j + 1][1];
        c = [Math.round(c0[0] + (c1[0] - c0[0]) * t),
             Math.round(c0[1] + (c1[1] - c0[1]) * t),
             Math.round(c0[2] + (c1[2] - c0[2]) * t)];
        break;
      }
    }
    canopyLut.push(c);
  }
  return canopyLut;
}
function canopyHeightFromRGB(r, g, b) {
  var lut = canopyLutBuild();
  var best = 0, bestD = Infinity;
  for (var i = 0; i < lut.length; i++) {
    var dr = lut[i][0] - r, dg = lut[i][1] - g, db = lut[i][2] - b;
    var d = dr * dr + dg * dg + db * db;
    if (d < bestD) { bestD = d; best = i; }
  }
  return best * 25 / 256;
}
/* One cached tile: the tile the cursor is over, drawn to an
   offscreen canvas so a pixel read is cheap. Reloaded only
   when the cursor crosses into another tile. */
var canopyTileCache = { key: null, canvas: null, loaded: false };
var canopyReadoutEl = null;
var canopyLastLatLng = null;
function canopyTileXY(latlng, z) {
  var n = Math.pow(2, z);
  var x = Math.floor((latlng.lng + 180) / 360 * n);
  var latRad = latlng.lat * Math.PI / 180;
  var y = Math.floor((1 - Math.log(Math.tan(latRad) +
    1 / Math.cos(latRad)) / Math.PI) / 2 * n);
  var fx = ((latlng.lng + 180) / 360 * n - x) * 256;
  var fy = ((1 - Math.log(Math.tan(latRad) +
    1 / Math.cos(latRad)) / Math.PI) / 2 * n - y) * 256;
  return { x: x, y: y,
           px: Math.max(0, Math.min(255, Math.floor(fx))),
           py: Math.max(0, Math.min(255, Math.floor(fy))) };
}
function canopyReadoutShow(latlng) {
  if (!canopyReadoutEl) return;
  var def = layerById("treeheight");
  if (!def || !def.layer || !map.hasLayer(def.layer)) {
    canopyReadoutEl.textContent =
      "Hover the canopy to read its height.";
    return;
  }
  var z = Math.min(map.getZoom(), 15);
  var t = canopyTileXY(latlng, z);
  var key = z + "/" + t.x + "/" + t.y;
  function readPixel() {
    if (!canopyTileCache.canvas) return;
    var ctx = canopyTileCache.canvas.getContext("2d");
    var d = ctx.getImageData(t.px, t.py, 1, 1).data;
    if (d[3] === 0) {
      canopyReadoutEl.textContent = "No canopy data here.";
      return;
    }
    var h = canopyHeightFromRGB(d[0], d[1], d[2]);
    canopyReadoutEl.textContent =
      "Canopy height here: " + h.toFixed(1) + " m";
  }
  if (canopyTileCache.key === key && canopyTileCache.loaded) {
    readPixel();
    return;
  }
  if (canopyTileCache.key === key) return; /* tile still loading */
  canopyTileCache = { key: key, canvas: null, loaded: false };
  var img = new Image();
  img.onload = function () {
    if (canopyTileCache.key !== key) return;
    var c = document.createElement("canvas");
    c.width = 256; c.height = 256;
    c.getContext("2d").drawImage(img, 0, 0);
    canopyTileCache.canvas = c;
    canopyTileCache.loaded = true;
    /* Re-read for wherever the cursor is now. */
    if (canopyLastLatLng) canopyReadoutShow(canopyLastLatLng);
  };
  img.onerror = function () {
    canopyTileCache = { key: null, canvas: null, loaded: false };
  };
  img.src = "tiles/canopy-height/" + key + ".png";
}
function wireCanopyHover() {
  map.on("mousemove", function (e) {
    canopyLastLatLng = e.latlng;
    canopyReadoutShow(e.latlng);
  });
  map.on("mouseout", function () {
    canopyLastLatLng = null;
    if (canopyReadoutEl) {
      canopyReadoutEl.textContent =
        "Hover the canopy to read its height.";
    }
  });
}
/* Tree height overlay (§7): one opacity for the canopy-height
   colour. Default 70% — at 100% the dark green swallows
   the amber sections and the orange pins. Present mode drops
   it to 60% (R4) and restores it on exit. */
var treeHeightOpacity = 0.70;
var treeHeightSlider = null;
var treeHeightOpacityEl = null;
function setTreeHeightOpacity(v) {
  treeHeightOpacity = v;
  mnCanopyHeight.setOpacity(v);
  if (treeHeightSlider) {
    treeHeightSlider.value = String(Math.round(v * 100));
  }
  if (treeHeightOpacityEl) {
    treeHeightOpacityEl.textContent =
      Math.round(v * 100) + "%";
  }
}

/* Height lines (§7): smoothed 5 m contours. Normal mode shows
   all five levels thin; Present mode shows only 10/20/25 m,
   thicker — the 5 m interval is unreadable from the back of a
   room. The layer only draws at z ≥ 12 (applyContoursGate). */
var contoursLayerRef = null;
function contourStyle(f) {
  var level = (f.properties || {}).level;
  if (document.body.classList.contains("present")) {
    if (level === 5 || level === 15) return { opacity: 0, weight: 0 };
    return { color: "#8a6d1a", weight: 2.5, opacity: 0.8 };
  }
  return { color: "#8a6d1a", weight: 1, opacity: 0.55 };
}
function applyContoursGate() {
  var def = layerById("contours");
  if (!def || !def.layer) return;
  var show = def.box && def.box.checked && map.getZoom() >= 12;
  if (show) {
    if (!map.hasLayer(def.layer)) def.layer.addTo(map);
  } else {
    if (map.hasLayer(def.layer)) map.removeLayer(def.layer);
  }
}

var LAYERS = [
  {
    id: "trail", label: "NCTA Trail", file: "data/trail.geojson",
    onByDefault: true, group: "The trail",
    swatch: { kind: "line", color: CHAPTER_COLORS.ITM },
    build: function (gj) {
      var casing = L.geoJSON(gj, {
        renderer: canvasFor(), interactive: false,
        style: trailCasingStyle,
      });
      var core = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: trailStyle,
        onEachFeature: function (f, l) { bindPop(l, trailPopup(f)); },
      });
      trailCasingLayer = casing;
      trailCoreLayer = core;
      var group = L.featureGroup([casing, core]);
      group.bringToFront = function () {
        casing.bringToFront(); core.bringToFront();
      };
      return group;
    },
  },
  {
    id: "stretches", label: "Adopted sections",
    file: "data/stretches.geojson", onByDefault: true, group: "The trail",
    swatch: { kind: "line", color: STRETCH_STYLE.color },
    build: function (gj) {
      var casing = L.geoJSON(gj, {
        renderer: canvasFor(), interactive: false,
        style: stretchCasingStyle,
      });
      stretchCasingLayer = casing;
      /* Touch targets: canvas lines are thin, so on coarse
         pointers a fat near-invisible underlay takes the taps
         (UX Part 1). */
      var underlay = null;
      if (COARSE_POINTER) {
        underlay = L.geoJSON(gj, {
          renderer: canvasFor(),
          style: { color: COLORS.adopted, weight: 14, opacity: 0.02 },
          onEachFeature: function (f, l) {
            l.on("click", function () {
              var item = walkByName[f.properties.name];
              if (item) {
                suppressMapClear = true;
                window.setTimeout(function () {
                  suppressMapClear = false;
                }, 0);
                selectSection(item, "map");
              }
            });
          },
        });
      }
      var lines = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: stretchStyle,
        onEachFeature: function (f, l) {
          var p = f.properties;
          var item = {
            type: "section", name: p.name, feature: f, layer: l,
            chainage: p.chainage_start_mi || 0,
          };
          l._walkItem = item;
          if (p.name) {
            registerWalkItem(item);
            /* Section name as a permanent tooltip near mid-section;
               layoutAnnotations() re-places it at every zoom so
               it never touches the line (Paul, 2026-11-10), and the
               label itself is CLICKABLE — same selection as the
               line (Paul: "you should be able to click on the name
               of the segment or the segment line"). */
            l.bindTooltip(p.name, {
              permanent: true, direction: "top", offset: [0, -17],
              className: "section-name-label", interactive: true,
            });
            var ttEl = l.getTooltip() && l.getTooltip().getElement();
            if (ttEl) {
              ttEl.style.pointerEvents = "auto";
              ttEl.style.cursor = "pointer";
              ttEl.addEventListener("click", function () {
                suppressMapClear = true;
                window.setTimeout(function () {
                  suppressMapClear = false;
                }, 0);
                selectSection(item, "map");
              });
            }
            sectionLabelItems.push({
              layer: l, name: p.name, feature: f,
              len: p.length_mi || 0,
            });
          }
          l.on("click", function () {
            suppressMapClear = true;
            window.setTimeout(function () {
              suppressMapClear = false;
            }, 0);
            selectSection(item, "map");
          });
          l.on("mouseover", function (e) {
            /* v6: placement is computed per-zoom by
               layoutAnnotations(); the hover chip just needs a
               direction — above the line is the house default. */
            armChip(l, f, e.latlng, { direction: "top", offset: [0, -10] });
          });
          l.on("mouseout", closeChip);
        },
      });
      stretchLinesLayer = lines;
      var children = [casing];
      if (underlay) children.push(underlay);
      children.push(lines);
      var group = L.featureGroup(children);
      group.bringToFront = function () {
        casing.bringToFront();
        if (underlay) underlay.bringToFront();
        lines.bringToFront();
      };
      group.on("add", function () {
        window.setTimeout(layoutAnnotations, 60);
      });
      return group;
    },
  },
  {
    /* Boundary markers delineate the adopted sections and have
       their own toggle (Paul, Nov 11, 2026: "Adoption segment
       ends"). The INITIAL state is derived once from the Adopted
       sections toggle (defaultFrom, applied in the panel builder
       and in applyHash); after load the two toggles are fully
       independent — sections no longer drag the ends with them.
       Chapter termini are the separate "termini" layer below and
       stay on independently. */
    id: "boundaries", label: "Adoption segment ends",
    file: "data/boundaries.geojson", onByDefault: true,
    group: "The trail", defaultFrom: "stretches",
    swatch: { kind: "bar", color: COLORS.tick },
    build: function (gj) {
      /* Each boundary is a bar struck ACROSS the line, perpendicular
         to the trail's bearing at that point (tick endpoints computed
         by the site-data build), with NO text: Paul's design
         corrections (2026-11-10): bars, not dots, and nothing
         labelled at segment ends. The bar's length SCALES WITH ZOOM
         up to a cap (see layoutTickSet). Softened in v4 (DESIGN
         D5): slate core, lighter casing — authority without
         shouting over the section names. */
      var items = [];
      gj.features.forEach(function (f) {
        if (f.properties.chapter_end || !f.properties.tick) return;
        var t = f.properties.tick;
        var casing = L.polyline([], { renderer: canvasFor(),
          interactive: false, color: COLORS.casing, weight: 5,
          opacity: 0.85 });
        var core = L.polyline([], { renderer: canvasFor(),
          interactive: false, color: COLORS.tick, weight: 2.75,
          opacity: 1 });
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
      window.setTimeout(layoutAnnotations, 60);
      return boundaryTickGroup;
    },
  },
  {
    /* S1 measured spine: a slate numeral on the line every 10
       chapter miles from the west end, placed by the annotation
       pass at section-name priority. The 5-mile points ride the
       same layer, CSS-hidden on screen, so print can show the
       5-mile cadence (S5). No toggle of its own — it is
       annotation, like the section names. These are RELATIVE
       miles from the west end, never NCT/state miles. */
    id: "chainage", label: "Chainage (miles from west end)",
    file: "data/chainage.geojson", onByDefault: true,
    hiddenToggle: true,
    build: function (gj) {
      var group = L.layerGroup();
      chainageGroupRef = group;
      chainageItems = [];
      gj.features.forEach(function (f) {
        var c = f.geometry.coordinates;
        var ll = L.latLng(c[1], c[0]);
        var ten = !!f.properties.every10;
        var m = L.marker(ll, {
          interactive: false, keyboard: false,
          icon: L.divIcon({
            className: "map-label chainage-label", iconSize: [0, 0],
            html: "<span class='ch-num" + (ten ? "" : " five") +
              "'>" + f.properties.miles_from_west + "</span>",
          }),
        });
        chainageItems.push({ marker: m, latlng: ll,
          miles: f.properties.miles_from_west, every10: ten });
        /* 5-mile markers are added unconditionally (print shows
           them; screen CSS hides them). The annotation pass adds
           and removes the 10-mile markers by collision. */
        if (!ten) group.addLayer(m);
      });
      group.on("add", function () {
        window.setTimeout(layoutAnnotations, 60);
      });
      return group;
    },
  },
  {
    id: "termini", label: "Chapter boundaries",
    file: "data/boundaries.geojson", onByDefault: true, group: "The trail",
    swatch: { kind: "bar", color: CHAPTER_COLORS.ITM },
    build: function (gj) {
      var ends = gj.features.filter(function (f) {
        return f.properties.chapter_end;
      });
      ends.sort(function (a, b) {
        return a.geometry.coordinates[0] - b.geometry.coordinates[0];
      });
      var group = L.layerGroup();
      layoutTicks();
      window.setTimeout(layoutAnnotations, 60);
      ends.forEach(function (f, i) {
        var c = f.geometry.coordinates;
        var which = i === 0 ? "west end"
          : (i === ends.length - 1 ? "east end" : "end");
        /* The chapter's own ends get the same visual language as
           the section boundaries, with more weight: the tick
           stretched to ~56 px on screen (≈2.5× the section ticks,
           floored at ~280 m, capped at 4.2 km), in chapter green
           with a white casing, plus the terminus name (the chapter
           delineation Paul asked for — section ends stay
           unlabelled, chapter ends are labelled). */
        if (f.properties.tick) {
          var t = f.properties.tick;
          var casing = L.polyline([], { renderer: canvasFor(),
            interactive: false, color: COLORS.casing, weight: 8,
            opacity: 0.9 });
          var core = L.polyline([], { renderer: canvasFor(),
            interactive: false, color: COLORS.trail, weight: 4.5,
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
    id: "gaps", label: "Adoption gap",
    file: "data/gaps.geojson", onByDefault: true, group: "The trail",
    swatch: { kind: "line", color: GAP_CORE_STYLE.color, dashed: true },
    build: function (gj) {
      var casing = L.geoJSON(gj, { renderer: canvasFor(),
                                   style: gapCasingStyle });
      gapCasingLayer = casing;
      var core = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: GAP_CORE_STYLE,
        onEachFeature: function (f, l) {
          var item = {
            type: "gap", name: f.properties.gap_id || "GAP-W",
            feature: f, layer: l, chainage: 0,
          };
          registerWalkItem(item);
          l.on("click", function () {
            suppressMapClear = true;
            window.setTimeout(function () {
              suppressMapClear = false;
            }, 0);
            selectSection(item, "map");
          });
          l.on("mouseover", function (e) {
            armChip(l, f, e.latlng, { direction: "top", offset: [0, -8] });
          });
          l.on("mouseout", closeChip);
        },
      });
      /* The gap carries its name on the map (DESIGN D4), in the
         terminus-label idiom but the gap's voice, at z ≥ 9. */
      var labelGroup = L.layerGroup();
      gapLabelGroupRef = labelGroup;
      gj.features.forEach(function (f) {
        var parts = featureLatLngs(f);
        if (!parts.length) return;
        var center = L.latLngBounds(parts[0]).getCenter();
        var lenTxt = f.properties.length_mi != null
          ? f.properties.length_mi.toFixed(1) : "?";
        var m = L.marker(center, {
          keyboard: false,
          icon: L.divIcon({
            className: "map-label gap-label", iconSize: [0, 0],
            html: "<span>Not adopted — " + lenTxt + " mi</span>",
          }),
        });
        m.on("click", function () {
          suppressMapClear = true;
          window.setTimeout(function () {
            suppressMapClear = false;
          }, 0);
          if (gapWalkItem) selectSection(gapWalkItem, "map");
        });
        gapLabelMarkers.push(m);
      });
      gapCoreLayer = core;
      var group = L.featureGroup([casing, core, labelGroup]);
      gapsGroupRef = group;
      group.bringToFront = function () {
        casing.bringToFront();
        core.bringToFront();
      };
      group.on("add", function () {
        window.setTimeout(layoutGapLabels, 30);
        window.setTimeout(updateGapMarch, 30);
      });
      return group;
    },
  },
  {
    /* M2: the state (NCTA) half-mile points, snapped to the drawn
       lines in the site build. Whole miles wear the slate disc
       with a white ring; halves a smaller plain dot. Labels are
       the bare state-mile number, whole miles only at Z3+ (halves
       at Z4), placed by the unified annotation pass at the lowest
       priority. Default OFF — this is a second mileage reckoning
       on the face (see M3 in the spec) and stays opt-in. */
    id: "milemarkers", label: "NCTA mile markers",
    title: "NCTA mileage — a different reckoning from the " +
      "chapter tracker's miles",
    file: "data/milemarkers.geojson", onByDefault: false,
    group: "The trail",
    swatch: { kind: "pin", color: COLORS.tick },
    build: function (gj) {
      mileLabelItems = [];
      var layer = L.geoJSON(gj, {
        pointToLayer: function (f, latlng) {
          var whole = f.properties.index_ === "Index";
          var m = L.circleMarker(latlng, whole ? {
            radius: 3.5, color: "#ffffff", weight: 1.5,
            fillColor: COLORS.tick, fillOpacity: 1,
          } : {
            radius: 2, color: COLORS.tick, weight: 0,
            fillColor: COLORS.tick, fillOpacity: 0.75,
          });
          if (f.properties.label != null) {
            m.bindTooltip(String(f.properties.label), {
              permanent: true, direction: "top", offset: [0, -6],
              className: "mile-label", interactive: false,
            });
            mileLabelItems.push({ layer: m, isHalf: !whole,
              latlng: latlng, num: f.properties.label });
          }
          return m;
        },
      });
      layer.on("add", function () {
        window.setTimeout(layoutAnnotations, 60);
      });
      return layer;
    },
  },
  {
    /* Parcels re-enabled Nov 10, 2026 (evening, Paul): the layer
       is back in the panel, OFF by default, and LAZY — nothing
       fetches data/parcels.geojson until the box is first checked
       (ensureLayer is only called from the toggle handler or a
       #layers=parcels hash, never at startup). */
    id: "parcels", label: "Public parcels",
    file: "data/parcels.geojson", onByDefault: false, group: "Around the trail",
    swatch: { kind: "fill", color: "#fdbb84", border: "#b35806" },
    build: function (gj) {
      var layer = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: parcelStyle,
        onEachFeature: function (f, l) { bindPop(l, parcelPopup(f)); },
      });
      parcelsLayerRef = layer;
      return layer;
    },
  },
  {
    /* Leech Lake Reservation (Paul, Nov 11, 2026 — "put a
       specific polygon in for native nations"): the federal
       reservation boundary as published by the Bureau of
       Indian Affairs (AIAN Land Area Representation, LAR0033
       "Leech Lake"), pulled by
       scripts/pull_leech_lake_reservation.py. Switched from
       Census TIGER/Line the same day: the Census polygon
       stitched its southern lobe on with a ~5 m bridge that
       rendered as the boundary crossing itself; BIA draws the
       lobe as a separate polygon with a ~210 m gap. OFF by
       default and LAZY like parcels — nothing fetches
       data/leech-lake-reservation.geojson until the box is
       first checked. A quiet violet fill + outline, under the
       trail: a context layer, not a claim. The popup carries
       the source + vintage and the honest line (published
       boundary, not a legal survey). 2.34 mi of the depicted
       trail (Chip-12) lies inside. */
    id: "leechlake", label: "Leech Lake Reservation",
    title: "Leech Lake Reservation boundary (Leech Lake Band " +
      "of Ojibwe) — Bureau of Indian Affairs, AIAN-LAR",
    file: "data/leech-lake-reservation.geojson",
    onByDefault: false, group: "Around the trail",
    swatch: { kind: "fill", color: "#8e86c2", border: "#5e548e" },
    build: function (gj) {
      var group = L.layerGroup();
      var poly = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: {
          color: "#5e548e", weight: 2,
          fillColor: "#8e86c2", fillOpacity: 0.13,
        },
        onEachFeature: function (f, l) {
          bindPop(l, leechLakePopup(f));
        },
      });
      group.addLayer(poly);
      gj.features.forEach(function (f) {
        var p = f.properties;
        if (p.label_lat == null || p.label_lon == null) return;
        group.addLayer(L.marker(
          L.latLng(p.label_lat, p.label_lon), {
            keyboard: false, interactive: false,
            icon: L.divIcon({
              className: "reservation-label-wrap",
              iconSize: [170, 18], iconAnchor: [85, 9],
              html: "<span class='reservation-label'>" +
                "Leech Lake Reservation</span>",
            }),
          }));
      });
      return group;
    },
  },
  {
    /* Logging and burns (Phase 3, Nov 12, 2026): Cass County
       timber sales, current, clipped to the trail corridor
       (1,182 units, 2007–2026). OFF by default and LAZY like
       parcels — nothing fetches data/logging-cass-timber-
       sales.geojson until the box is first checked. No expiry
       or status in the source, so the popup shows the year
       prominently. */
    id: "logcass", label: "Cass timber sales",
    title: "Cass County timber sales, current — year is the sale year",
    file: "data/logging-cass-timber-sales.geojson",
    onByDefault: false, group: "The land",
    swatch: { kind: "fill", color: "#d97706", border: "#92400e" },
    build: function (gj) {
      var layer = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: function (f) {
          return timberSaleStyle(f, {
            color: "#92400e", weight: 1.5,
            fillColor: "#d97706", fillOpacity: 0.28,
          });
        },
        onEachFeature: function (f, l) { bindPop(l, logCassPopup(f)); },
      });
      return layer;
    },
  },
  {
    /* Cass County FIM (forest inventory) stands, current,
       clipped to the corridor (6,472 stands). OFF by default
       and LAZY. An inventory, not a sale — stand_age 0 means
       unrecorded. Geometry simplified to ~22 m for the viewer;
       no stands dropped. */
    id: "logfim", label: "Cass forest stands",
    title: "Cass County forest inventory stands",
    file: "data/logging-cass-fim-stands.geojson",
    onByDefault: false, group: "The land",
    swatch: { kind: "fill", color: "#6b8e23", border: "#556b2f" },
    build: function (gj) {
      var layer = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: {
          color: "#556b2f", weight: 1,
          fillColor: "#6b8e23", fillOpacity: 0.18,
        },
        onEachFeature: function (f, l) { bindPop(l, logFimPopup(f)); },
      });
      return layer;
    },
  },
  {
    /* USFS EDW timber sale project areas, Chippewa National
       Forest (124 areas). OFF by default and LAZY. These are
       project areas, not sale units — much larger than the
       Cass sale units — so they draw underneath them. */
    id: "logedw", label: "Chippewa NF timber sales",
    title: "USFS timber sale project areas, Chippewa National Forest",
    file: "data/logging-edw-timber-sale.geojson",
    onByDefault: false, group: "The land",
    swatch: { kind: "fill", color: "#64748b", border: "#475569" },
    build: function (gj) {
      var layer = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: function (f) {
          return timberSaleStyle(f, {
            color: "#475569", weight: 1.5,
            fillColor: "#64748b", fillOpacity: 0.15,
          });
        },
        onEachFeature: function (f, l) { bindPop(l, logEdwPopup(f)); },
      });
      return layer;
    },
  },
  {
    /* BWSR RIM Reserve conservation easements, clipped to the
       corridor (40 easements, 3,370 ac — 38 perpetual riparian,
       1 limited cropland, 1 PWP). OFF by default and LAZY like
       the logging layers. One easement is expired and is carried
       honestly with its expiry in the popup. */
    id: "easements", label: "Conservation easements",
    title: "BWSR RIM conservation easements in the corridor",
    file: "data/easements.geojson",
    onByDefault: false, group: "The land",
    swatch: { kind: "fill", color: "#0d9488", border: "#0f766e" },
    build: function (gj) {
      var layer = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: {
          color: "#0f766e", weight: 1.5,
          fillColor: "#0d9488", fillOpacity: 0.25,
        },
        onEachFeature: function (f, l) { bindPop(l, easementsPopup(f)); },
      });
      return layer;
    },
  },
  {
    id: "access", label: "Non-road access",
    title: "Forest roads, OHV, other trails",
    file: "data/access.geojson", onByDefault: false, group: "Around the trail",
    swatch: { kind: "line", color: ACCESS_STYLES.state_trail.color },
    build: function (gj) {
      var layer = L.geoJSON(gj, {
        renderer: canvasFor(),
        style: accessStyle,
        onEachFeature: function (f, l) {
          bindPop(l, accessPopup(f));
          wireContextHover(l, f, "access");
        },
      });
      accessLayerRef = layer;
      return layer;
    },
  },
  {
    id: "roads", label: "Roads", file: "data/roads.geojson",
    onByDefault: false, group: "Around the trail",
    swatch: { kind: "line", color: ROADS_STYLE.color },
    build: function (gj) {
      /* §2.10/§2.12: four class sublayers drawn C, B, F, A (minor
         roads settle first, arterials land on top). */
      var subs = ["C", "B", "F", "A"].map(function (cls) {
        return L.geoJSON({
          type: "FeatureCollection",
          features: gj.features.filter(function (f) {
            return (f.properties.road_class || "C") === cls;
          }),
        }, {
          renderer: canvasFor(),
          style: roadStyle,
          onEachFeature: function (f, l) {
            bindPop(l, roadPopup(f));
            wireContextHover(l, f, "road");
          },
        });
      });
      var group = L.featureGroup(subs);
      roadsGroupRef = group;
      group.bringToFront = function () {
        subs.forEach(function (s) { s.bringToFront(); });
      };
      return group;
    },
  },
  {
    /* Trail alerts (Paul, Nov 10, 2026 — "add a Trail alerts
       layer next round"): NCTA's own alert points (closures,
       storm damage, reroutes, new routes), pulled verbatim by
       scripts/pull_trail_alerts.py. OFF by default and LAZY like
       parcels — nothing fetches data/trail-alerts.geojson until
       the box is first checked. The marker is a red warning
       diamond in the gap red — deliberately unlike the Places
       letter discs and the orange asset pins. No zoom gate:
       five markers should never hide. */
    id: "alerts", label: "Trail alerts",
    title: "Trail alerts from the North Country Trail Association" +
      " — closures, storm damage, reroutes",
    file: "data/trail-alerts.geojson", onByDefault: false,
    group: "Around the trail",
    swatch: { kind: "alert", color: COLORS.gap },
    build: function (gj) {
      return L.geoJSON(gj, {
        pointToLayer: function (f, latlng) {
          return L.marker(latlng, {
            keyboard: false,
            icon: L.divIcon({
              className: "alert-marker-wrap", iconSize: [18, 18],
              iconAnchor: [9, 9],
              html: "<span class='alert-marker'>" +
                "<span class='alert-glyph'>!</span></span>",
            }),
          });
        },
        onEachFeature: function (f, l) { bindPop(l, alertPopup(f)); },
      });
    },
  },
  {
    /* Chapter places (Paul, Nov 10, 2026 — "we need to be able
       to add campsites"): the chapter's OWN place records,
       separate from NCTA's data so re-pulls never overwrite
       them. Seeded from the NCTA camping points (each seed
       supersedes its NCTA point — see build_gazetteer.py), then
       hand-maintained through Paul; no editing UI on the public
       map. OFF by default and LAZY like parcels and alerts —
       nothing fetches data/chapter-places.geojson until the box
       is first checked. Markers are deep-green chapter discs —
       deliberately unlike the paper Places discs, the red alert
       diamonds and the orange asset pins; a CLOSED place greys
       out under a red ring and a diagonal bar. No zoom gate:
       the chapter's own places should never hide. */
    id: "chapterplaces", label: "Chapter places",
    title: "Places the chapter itself records — campsites first",
    file: "data/chapter-places.geojson", onByDefault: false,
    group: "ITM inventory",
    swatch: { kind: "chapter", color: COLORS.trailDeep },
    build: function (gj) {
      var glyphs = { Parking: "P", Camping: "C", Water: "W",
                     Shelter: "S", Privy: "R" };
      return L.geoJSON(gj, {
        pointToLayer: function (f, latlng) {
          var p = f.properties;
          var glyph = glyphs[p.kind];
          var closedCls = p.status === "closed" ? " closed" : "";
          var html = glyph
            ? "<span class='chapter-disc" + closedCls + "'>" +
              glyph + "</span>"
            : "<span class='chapter-dot" + closedCls + "'></span>";
          return L.marker(latlng, {
            keyboard: false,
            icon: L.divIcon({
              className: "chapter-disc-wrap", iconSize: [19, 19],
              iconAnchor: [10, 10],
              html: html,
            }),
          });
        },
        onEachFeature: function (f, l) {
          bindPop(l, chapterPopupHtml(f));
        },
      });
    },
  },
  {
    /* S4 Places: the gazetteer's 114 NCTA waypoints (parking,
       camping, water, shelters, POIs) as a map layer, Z3+ only.
       Letter discs in the terminus idiom; POIs are plain slate
       dots. Popups reuse the gazetteer record (gazPopupHtml), so
       the layer and Find can never disagree. */
    id: "places", label: "Places",
    title: "NCTA waypoints: parking, camping, water, shelters, " +
      "points of interest",
    file: "data/gazetteer.geojson", onByDefault: false,
    group: "ITM inventory",
    swatch: { kind: "pin", color: COLORS.tick },
    build: function (gj) {
      var inner = L.layerGroup();
      var outer = L.layerGroup();
      placesInnerRef = inner;
      placesOuterRef = outer;
      var glyphs = { Parking: "P", Camping: "C", Water: "W",
                     Shelter: "S" };
      gj.features.forEach(function (f) {
        var p = f.properties;
        /* Chapter entries ride the gazetteer for Find, but the
           Chapter places layer draws them — never both. */
        if (p.source === "chapter") return;
        var glyph = glyphs[p.kind];
        if (p.kind !== "POI" && !glyph) return;
        var c = f.geometry.coordinates;
        var ll = L.latLng(c[1], c[0]);
        var mk;
        if (p.kind === "POI") {
          mk = L.circleMarker(ll, {
            radius: 3, color: COLORS.tick, weight: 1,
            fillColor: COLORS.tick, fillOpacity: 0.8,
          });
        } else {
          mk = L.marker(ll, {
            keyboard: false,
            icon: L.divIcon({
              className: "place-disc-wrap", iconSize: [15, 15],
              iconAnchor: [8, 8],
              html: "<span class='place-disc'>" + glyph + "</span>",
            }),
          });
        }
        bindPop(mk, gazPopupHtml(f));
        inner.addLayer(mk);
      });
      outer.addLayer(inner);
      applyPlacesGate();
      return outer;
    },
  },
  {
    id: "assets", label: "Asset pins",
    file: "data/assets.geojson", onByDefault: true, missingOk: true,
    emptyUntilData: true, group: "ITM inventory",
    swatch: { kind: "pin", color: COLORS.assetPin },
    build: function (gj) {
      /* One sublayer per type (see ASSET_TYPE_TOGGLES): the
         panel's per-type checkboxes add and remove these from
         the group, so a type can be hidden without touching the
         others. The main Asset pins checkbox still controls the
         whole group. */
      var group = L.layerGroup();
      assetsTypeLayers = {};
      assetPins.length = 0; /* fresh registry if the layer ever rebuilds */
      ASSET_TYPE_TOGGLES.forEach(function (t) {
        var code = t[0];
        var feats = gj.features.filter(function (f) {
          return assetTypeCode(f) === code;
        });
        if (!feats.length) return;
        var sub = L.geoJSON(
          { type: "FeatureCollection", features: feats }, {
            pointToLayer: function (f, latlng) {
              return assetMarker(f, latlng);
            },
            onEachFeature: function (f, l) {
              /* Function content (Leaflet 1.9 calls it at open
                 time): the popup is built when it opens, not
                 when the layer loads, so it always reflects the
                 pin's current data. */
              bindPop(l, function () { return assetPopup(f); });
              /* Spiderfy owns the click: the default auto-open
                 would fire before the spiderfy handler and open
                 the popup on the first (fan-out) click. Keypress
                 opening is untouched. */
              l.off("click", l._openPopup, l);
              l.on("click", function () { onAssetPinClick(l, f); });
              wireAssetHover(l, f);
              assetPins.push({ layer: l, feature: f, latlng: L.latLng(
                f.geometry.coordinates[1], f.geometry.coordinates[0]) });
            },
          });
        sub._assetType = code;
        assetsTypeLayers[code] = sub;
        if (assetTypeOn[code]) group.addLayer(sub);
      });
      return group;
    },
    panelExtra: function (label) {
      var wrap = document.createElement("div");
      wrap.className = "asset-types";
      ASSET_TYPE_TOGGLES.forEach(function (t) {
        var code = t[0], count = t[1];
        var lab = document.createElement("label");
        var box = document.createElement("input");
        box.type = "checkbox";
        box.checked = !!assetTypeOn[code];
        assetTypeBoxes[code] = box; /* applyHash + the share writer read it */
        box.setAttribute("aria-label",
          assetTypeName(code) + " pins");
        lab.appendChild(box);
        lab.appendChild(document.createTextNode(
          assetTypeName(code) + " (" + count + ")"));
        box.addEventListener("change", function () {
          unspiderfy(); /* a hidden type must not leave a fanned pin behind */
          assetTypeOn[code] = box.checked;
          var sub = assetsTypeLayers[code];
          var def = layerById("assets");
          if (!sub || !def || !def.layer) { writeShareHash(); return; }
          if (box.checked) def.layer.addLayer(sub);
          else def.layer.removeLayer(sub);
          writeShareHash(); /* a type change is a new shareable view */
        });
        wrap.appendChild(lab);
      });
      label.parentNode.insertBefore(wrap, label.nextSibling);
    },
  },
  {
    /* §7 "The land" (design review, Nov 11, 2026): Tree height —
       the canopy-height colour as ONE overlay over any
       background, OFF by default, opacity slider default 70%.
       The tile set is transparent outside the corridor, so the
       overlay never paints a rectangle. The NW hillshade
       companion was removed Nov 12, 2026 (Paul) — the colour
       alone carries the height. Hovering the overlay reads the
       height in metres (see the canopy hover readout). The two
       canopy radios are retired from Background (see BASES). */
    id: "treeheight", label: "Tree height",
    title: "How tall the trees are, over any background",
    noFetch: true, onByDefault: false, group: "The land",
    swatch: { kind: "fill", color: "#64af5a", border: "#406f48" },
    build: function () {
      if (!map.getPane("treeColor")) {
        var pc = map.createPane("treeColor");
        pc.style.zIndex = 210;
      }
      mnCanopyHeight.options.pane = "treeColor";
      setTreeHeightOpacity(treeHeightOpacity);
      return mnCanopyHeight;
    },
    panelExtra: function (label) {
      var wrap = document.createElement("div");
      wrap.className = "land-extra";
      var op = document.createElement("div");
      op.className = "opacity";
      var opLabel = document.createElement("span");
      opLabel.textContent = "Strength";
      op.appendChild(opLabel);
      var slider = document.createElement("input");
      slider.type = "range";
      slider.min = "0"; slider.max = "100";
      slider.value = String(Math.round(treeHeightOpacity * 100));
      slider.setAttribute("aria-label",
        "Tree height overlay strength");
      op.appendChild(slider);
      var opVal = document.createElement("span");
      opVal.className = "opacity-val";
      opVal.textContent = slider.value + "%";
      op.appendChild(opVal);
      slider.addEventListener("input", function () {
        setTreeHeightOpacity(slider.value / 100);
        opVal.textContent = slider.value + "%";
      });
      wrap.appendChild(op);
      var key = document.createElement("div");
      key.className = "key";
      key.innerHTML =
        "<div class='strip'></div>" +
        "<div class='marks'><span style='left:8%'>2 m · head " +
        "height</span><span style='left:80%'>20 m · old " +
        "growth*</span></div>" +
        "<div class='ends'><span>Open ground</span>" +
        "<span>Young trees</span><span>Tall trees</span></div>" +
        "<p class='key-note'>*Height is a guide, not proof of " +
        "old growth.</p>";
      wrap.appendChild(key);
      /* Hover readout (Paul, Nov 12, 2026): the height under
         the cursor, read live from the canopy tile. */
      var ro = document.createElement("p");
      ro.className = "key-note canopy-readout";
      ro.textContent = "Hover the canopy to read its height.";
      wrap.appendChild(ro);
      canopyReadoutEl = ro;
      label.parentNode.insertBefore(wrap, label.nextSibling);
      treeHeightSlider = slider;
      treeHeightOpacityEl = opVal;
    },
  },
  {
    /* §7: Height lines — smoothed 5 m CHM contours
       (5/10/15/20/25). OFF by default; at low zoom five-metre
       contours are visual noise, so the layer only draws at
       z ≥ 12 (applyContoursGate). In Present mode only the
       10/20/25 m lines show, thicker (a room cannot read the
       5 m interval). 63k features, canvas-rendered, fetched
       lazily like every heavy layer. */
    id: "contours", label: "Height lines — every 5 m",
    title: "How steep is it?",
    file: "data/chm-contours.geojson", onByDefault: false,
    group: "The land",
    swatch: { kind: "line", color: "#8a6d1a" },
    gate: applyContoursGate,
    build: function (gj) {
      contoursLayerRef = L.geoJSON(gj, {
        renderer: canvasFor(), interactive: false,
        style: contourStyle,
      });
      applyContoursGate();
      return contoursLayerRef;
    },
  },
  {
    /* NCTA map sheets (Paul, Nov 11, 2026 — "make it another
       layer"): NCTA's own Minnesota map-series sheets MN-023 to
       MN-044 as image overlays, one per sheet, over any base.
       OFF by default and LAZY like parcels — nothing fetches
       data/ncta-sheets.geojson (or any sheet image) until the box
       is first checked. The source is the series GeoPDF
       (northcountrytrail.org/maps/mn_map_series.pdf, 3/16/2026
       edition): each page's georeferencing viewport gives the
       sheet frame's true lat/lon quad; the web derivative is the
       frame crop rendered at 200 dpi, <=1600 px wide, JPEG.
       Alignment was re-measured Nov 11, 2026 (docs/
       research-sheets-alignment-2026-11-11.md): the GeoPDF
       registration is exact to 1-3 m at most printed mile
       diamonds (19 diamonds, 4 sheets), and the trail line
       agrees with the mile points to a 1.5 m median — the data
       is fine. The images are placed by a 3-corner affine
       overlay (L.imageOverlay.rotated, vendored above) pinned
       to the quad's true TL/TR/BL corners: the quad deviates
       from a parallelogram by only 7.6-9.1 m at the fourth
       corner, so the affine residual is <= ~9 m everywhere
       (verified analytically in the same note; the old
       axis-aligned placement sheared content 80-150 m,
       103-256 m at corners, and doubled the trail up to 374 m
       in overlap strips). Sheet
       outlines + number labels ride the same toggle and stay
       visible at low zoom where 22 near-white sheets would just
       be a blanket. Overlay opacity 0.92 keeps the base faintly
       present at sheet seams. */
    id: "nctasheets", label: "NCTA map sheets",
    title: "The North Country Trail Association's printed " +
      "Minnesota map sheets (MN-023 to MN-044), laid over the map",
    file: "data/ncta-sheets.geojson", onByDefault: false,
    group: "Around the trail",
    swatch: { kind: "fill", color: "#fdf6d8", border: "#8a6d1a" },
    build: function (gj) {
      var group = L.layerGroup();
      gj.features.forEach(function (f) {
        var p = f.properties;
        /* The frame's true lat/lon quad rides the feature
           geometry: ring order BL, BR, TR, TL in [lon, lat].
           Place the image by its real TL/TR/BL corners (3-corner
           affine) instead of the quad's axis-aligned bounds —
           the old axis-aligned placement sheared printed content
           80-150 m, 103-256 m at corners (Nov 11, 2026,
           docs/research-sheets-alignment-2026-11-11.md). */
        var quad = f.geometry.coordinates[0];
        var img = L.imageOverlay.rotated(p.image,
          L.latLng(quad[3][1], quad[3][0]),
          L.latLng(quad[2][1], quad[2][0]),
          L.latLng(quad[0][1], quad[0][0]), {
            opacity: 0.92, interactive: false,
          });
        img._sheetGroup = group;
        sheetImages.push(img);
        if (map.getZoom() >= 11) group.addLayer(img);
        var outline = L.geoJSON(f, {
          interactive: true,
          style: { color: "#8a6d1a", weight: 1.5, dashArray: "6 4",
                   fill: false },
          onEachFeature: function (feat, l) {
            bindPop(l, "<strong>Official NCTA sheet " +
              esc(p.sheet) + "</strong><br>NCTA miles " +
              esc(p.miles) + "<br><a href='" + NCTA_SHEET_PDF +
              "#page=" + p.page + "' target='_blank' " +
              "rel='noopener'>Open this sheet in the NCTA " +
              "Minnesota series PDF</a>");
          },
        });
        group.addLayer(outline);
        var ring = f.geometry.coordinates[0];
        var clat = (ring[0][1] + ring[2][1]) / 2;
        var clon = (ring[0][0] + ring[2][0]) / 2;
        var lab = L.marker(L.latLng(clat, clon), {
          keyboard: false, interactive: false,
          icon: L.divIcon({
            className: "sheet-label-wrap", iconSize: [64, 18],
            iconAnchor: [32, 9],
            html: "<span class='sheet-label'>" + esc(p.sheet) +
              "</span>",
          }),
        });
        group.addLayer(lab);
      });
      return group;
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

/* --------------------------------------------------- Present mode
   R4 (design review, Nov 11, 2026): a meeting-room mode — the
   panel hides, the type grows, and the strip along the bottom
   carries the one line a room needs. Triggered by the panel's
   "Present" button, by the Work view, or by the keyboard
   shortcut "p" (which also turns it off). The panel can be
   brought back with the "Show panel" button. */
var presentMode = false;
var savedTreeHeightOpacity = null;
function setPresent(on) {
  presentMode = !!on;
  document.body.classList.toggle("present", presentMode);
  var strip = document.getElementById("present-strip");
  if (strip) strip.hidden = !presentMode;
  var showBtn = document.getElementById("show-panel-btn");
  if (showBtn) showBtn.hidden = !presentMode;
  /* Present mode is the Work view, not a separate state —
     switching views tracks it. Exiting Present leaves the
     view where it was (Work) — the panel comes back, the
     view does not change. */
  if (presentMode) setView("work");
  /* §7: the tree-height overlay runs at 60% in a room (the
     70% default swallows the amber sections on a projector);
     the user's own setting is restored on exit. */
  if (presentMode) {
    savedTreeHeightOpacity = treeHeightOpacity;
    setTreeHeightOpacity(0.60);
  } else if (savedTreeHeightOpacity != null) {
    setTreeHeightOpacity(savedTreeHeightOpacity);
    savedTreeHeightOpacity = null;
  }
  if (contoursLayerRef) contoursLayerRef.setStyle(contourStyle);
  applyContoursGate();
  updatePresentStrip();
  updatePresentKey();
  if (presentMode) map.invalidateSize();
}
function updatePresentStrip() {
  var strip = document.getElementById("present-strip");
  if (!strip) return;
  strip.textContent = "2.9 mi unadopted · Chip-5 and Chip-6";
}
/* The tree-height key in Present mode: the panel (and its key)
   is hidden in a room, so the key rides in its own fixed
   element — shown only while the overlay is on. */
function updatePresentKey() {
  var pk = document.getElementById("present-key");
  if (!pk) return;
  var treeDef = layerById("treeheight");
  var on = presentMode && treeDef && treeDef.box && treeDef.box.checked;
  if (!on) { pk.hidden = true; return; }
  var key = document.querySelector(".land-extra .key");
  if (!key) { pk.hidden = true; return; }
  pk.innerHTML = key.outerHTML;
  pk.hidden = false;
}
document.addEventListener("keydown", function (e) {
  var t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
      t.tagName === "SELECT" || t.isContentEditable)) return;
  if (e.key === "p" || e.key === "P") setPresent(!presentMode);
  if (e.key === "Escape" && presentMode) setPresent(false);
});

/* --------------------------------------------------- view switch
   R6 (design review, Nov 11, 2026): three views — Work,
   Explore, Visit — as PRESETS over the same data, not three
   maps. The switch is the first thing under the title; the
   panel groups re-sort under it, and only the layer toggles
   change. Default is Explore (the current home screen).
   Work = Present mode (panel hidden, work list first) and is
   also what the "Present" button and the "p" key reach.
   The choice is remembered in localStorage; a shared link
   carries it as #view=work|explore|visit. */
var currentView = "work";
var VIEW_PRESETS = {
  /* Work: the panel as redesigned — the adoption gap on,
     the assets and places on. Tree height stays OFF by
     default (Paul, Nov 12) — it is a toggle the reader turns
     on; Height lines stay off (they are a close-zoom tool). */
  work: { on: ["gaps", "assets", "places",
               "chapterplaces"],
          off: ["treeheight", "contours"] },
  /* Explore: the same map with the management toggles
     hidden and the trail + places + chapter places on.
     The assets (photos) stay on. */
  explore: { on: ["assets", "places", "chapterplaces"],
             off: ["treeheight", "contours"] },
  /* Visit: the public face — the trail, the places, the
     photos; the land stays off, and the panel shows nothing
     beyond Find and the welcome line. */
  visit: { on: ["assets", "places", "chapterplaces"],
           off: ["treeheight", "contours"] },
};
function setView(view) {
  if (!VIEW_PRESETS[view]) view = "explore";
  currentView = view;
  var preset = VIEW_PRESETS[view];
  (preset.on || []).forEach(function (id) {
    var def = layerById(id);
    if (!def || !def.box) return;
    if (!def.box.checked) { def.box.checked = true; ensureLayer(def, false); }
  });
  (preset.off || []).forEach(function (id) {
    var def = layerById(id);
    if (!def || !def.box) return;
    if (def.box.checked) {
      def.box.checked = false;
      if (def.layer) map.removeLayer(def.layer);
    }
  });
  var sw = document.getElementById("view-switch");
  if (sw) {
    var btns = sw.querySelectorAll("button");
    for (var i = 0; i < btns.length; i++) {
      var on = btns[i].getAttribute("data-view") === view;
      btns[i].classList.toggle("on", on);
      btns[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }
  /* The work list leads the panel in Work view; the title block
     leads it everywhere else (R2). Explore hides the work list
     and the management toggles; Visit hides the panel chrome
     beyond Find and the welcome line (R6) — the CSS reads
     these classes. */
  document.body.classList.toggle("view-work", view === "work");
  document.body.classList.toggle("view-explore", view === "explore");
  document.body.classList.toggle("view-visit", view === "visit");
  updatePresentStrip();
  try { localStorage.setItem("itm-view", view); } catch (e) {}
  /* A view change is a new shareable view — the writer records
     the full state (view, centre, base, layers, types). During
     load shareHashReady is false, so the preset application here
     never clobbers an incoming link; applyHash turns the writer
     on once the link is applied. */
  writeShareHash();
}
(function initView() {
  /* Default is Work — the mockup's home-screen state (work
     list leading, tree height on). A saved choice or a
     #view=… link wins over the default. */
  var view = "work";
  try {
    var saved = localStorage.getItem("itm-view");
    if (saved && VIEW_PRESETS[saved]) view = saved;
  } catch (e) {}
  var m = /(?:#|&)v=(work|explore|visit)/.exec(location.hash || "");
  if (m) view = m[1];
  currentView = view;
  /* The toggles are applied once the panel exists (the panel
     builder calls applyViewPreset); the switch buttons and the
     body class are set here so the first paint is right. */
  var sw = document.getElementById("view-switch");
  if (sw) {
    var btns = sw.querySelectorAll("button");
    for (var i = 0; i < btns.length; i++) {
      var on = btns[i].getAttribute("data-view") === view;
      btns[i].classList.toggle("on", on);
      btns[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }
  document.body.classList.toggle("view-work", view === "work");
  document.body.classList.toggle("view-explore", view === "explore");
  document.body.classList.toggle("view-visit", view === "visit");
})();

/* ------------------------------------------------- shareable view
   (Paul, Nov 12, 2026): the URL hash carries the whole viewer
   state, so a copied link opens exactly what the sender sees.
   HASH FORMAT — keep it stable; old shared links must keep
   opening. Params, in canonical order:
     v=work|explore|visit    view preset
     view=lat,lng,zoom        centre (5 decimals) + zoom
     base=topo|aerial|...     background, by BASES code
     layers=id,-id,...        EVERY layer toggle (id = on, -id = off)
     types=CP,SG,-BW,...      EVERY asset-type toggle, same convention
   The writer always records the FULL state, so a link is exact
   and self-contained. The reader (applyHash) is delta-tolerant:
   an old link that lists only some layers still works — listed
   tokens win, unlisted layers keep their state. */
var shareHashReady = false; /* false until applyHash has run, so the
   preset application during load never clobbers an incoming link */
function writeShareHash() {
  if (!shareHashReady || !history.replaceState) return;
  var c = map.getCenter();
  var parts = ["v=" + currentView,
    "view=" + c.lat.toFixed(5) + "," + c.lng.toFixed(5) + "," +
      map.getZoom(),
    "base=" + (currentBase && currentBase.code ?
      currentBase.code : "topo")];
  var layerParts = [];
  LAYERS.forEach(function (def) {
    if (def.enabled === false || !def.box) return;
    layerParts.push(def.box.checked ? def.id : "-" + def.id);
  });
  parts.push("layers=" + layerParts.join(","));
  var typeParts = [];
  ASSET_TYPE_TOGGLES.forEach(function (t) {
    typeParts.push(assetTypeOn[t[0]] ? t[0] : "-" + t[0]);
  });
  parts.push("types=" + typeParts.join(","));
  history.replaceState(null, "", "#" + parts.join("&"));
}

/* Panel groups (design review R2): the panel is organized by
   task, not by data source. The LAYERS array order is the build
   order; the PANEL order is this list, so a def's group decides
   where its toggle lands, not its position in the array. */
var PANEL_GROUPS = ["The trail", "ITM inventory",
                    "The land", "Around the trail"];
LAYERS.forEach(function (def) {
  def.layer = null;
  def.loading = false;
  if (def.enabled === false) { def.box = null; return; }
  var label = document.createElement("label");
  var box = document.createElement("input");
  box.type = "checkbox";
  box.checked = def.onByDefault;
  if (def.defaultFrom) {
    /* One-time initial-state derivation (Adoption segment ends
       start from the Adopted sections state). This runs only here,
       at panel build — never on later toggle changes. The source
       def precedes this one in LAYERS, so its box already exists. */
    var srcDef = layerById(def.defaultFrom);
    if (srcDef && srcDef.box) box.checked = srcDef.box.checked;
  }
  label.appendChild(box);
  var sw = document.createElement("span");
  sw.innerHTML = swatchFor(def);
  label.appendChild(sw.firstChild || document.createTextNode(""));
  label.appendChild(document.createTextNode(def.label));
  if (def.title) label.title = def.title;
  var suffix = null;
  if (def.emptyUntilData) {
    suffix = document.createElement("span");
    suffix.className = "tog-suffix";
    suffix.textContent = "(no photos yet)";
    label.appendChild(suffix);
    box.disabled = true;
    label.classList.add("disabled");
  }
  var errEl = document.createElement("div");
  errEl.className = "tog-error";
  errEl.hidden = true;
  def.box = box;
  def.errEl = errEl;
  def._label = label;
  box.addEventListener("change", function () {
    if (box.checked) { ensureLayer(def, true); }
    else if (def.layer) { map.removeLayer(def.layer); }
    if (def.id === "treeheight") updatePresentKey();
    /* No cross-toggle mirroring: Adoption segment ends are
       controlled only by their own checkbox (Nov 11, 2026). */
    writeShareHash(); /* a layer change is a new shareable view */
  });
  if (def.emptyUntilData) {
    /* Probe once: if the inventory file exists after all, wake the
       toggle up (UX P4 — a checked-but-empty control teaches users
       to distrust the others). */
    fetch(def.file).then(function (r) {
      if (!r.ok) return;
      box.disabled = false;
      label.classList.remove("disabled");
      if (suffix) suffix.textContent = "";
    }).catch(function () {});
  }
  /* Start whatever the box starts as — for most defs that is just
     onByDefault; for a defaultFrom def it is the derived state. */
  if (box.checked) ensureLayer(def, false);
});
/* Phase 2: lay the toggles out in panel (task) order. */
PANEL_GROUPS.forEach(function (group) {
  var container = togglesEl;
  if (!container) return;
  var headed = false;
  LAYERS.forEach(function (def) {
    if (def.enabled === false || !def._label) return;
    if (def.group !== group || def.hiddenToggle) return;
    if (!headed) {
      var gh = document.createElement("div");
      gh.className = "tog-group";
      gh.textContent = group;
      container.appendChild(gh);
      headed = true;
    }
    container.appendChild(def._label);
    container.appendChild(def.errEl);
    if (def.panelExtra) def.panelExtra(def._label);
  });
});
/* Apply the current view's preset now that the toggles exist
   (R6) — the onByDefault states are the Work view's, so this
   is a no-op for the default view except for Tree height,
   which the Work preset switches on. An explicit #layers=
   hash below still wins over the preset. */
setView(currentView);

/* Canopy hover readout (Paul, Nov 12, 2026): the mousemove
   wiring lives here, after the panel exists, so the readout
   element the panelExtra created is already in place. */
wireCanopyHover();

/* Wire the panel's own buttons (R4/R6/R7): the view switch,
   Present, Hide panel, and the footer About link (Sources
   behind it). */
(function wirePanelButtons() {
  var sw = document.getElementById("view-switch");
  if (sw) {
    var btns = sw.querySelectorAll("button");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () {
        setView(this.getAttribute("data-view"));
      });
    }
  }
  var presentBtn = document.getElementById("present-btn");
  if (presentBtn) presentBtn.addEventListener("click", function () {
    setPresent(true);
  });
  var hideBtn = document.getElementById("hide-panel-link");
  if (hideBtn) hideBtn.addEventListener("click", function () {
    setPresent(true);
  });
  var showBtn = document.getElementById("show-panel-btn");
  if (showBtn) showBtn.addEventListener("click", function () {
    setPresent(false);
  });
  /* R7: the footer About link opens the Sources card (the
     card stays where it is, in the corner — the link just
     reaches it, so nobody scrolls past 25 lines of provenance
     to reach the layers). */
  var about = document.getElementById("about-link");
  if (about) about.addEventListener("click", function (e) {
    e.preventDefault();
    var card = document.getElementById("sources-card");
    var btn = document.getElementById("btn-sources");
    if (card && card.hidden && btn) btn.click();
  });
  /* Copy link (Paul, Nov 12, 2026): copies the current URL with
     the up-to-date share hash, so the recipient opens exactly
     this view. Clipboard API where it exists (https / localhost),
     textarea + execCommand fallback for plain http. */
  var copyLinkBtn = document.getElementById("copy-link-btn");
  if (copyLinkBtn) copyLinkBtn.addEventListener("click", function () {
    writeShareHash(); /* the hash must carry the state as of now */
    var url = location.href;
    function done(ok) {
      copyLinkBtn.textContent = ok ? "Copied" :
        "Copy failed — copy the address bar";
      window.setTimeout(function () {
        copyLinkBtn.textContent = "Copy link";
      }, 2000);
    }
    function fallbackCopy(text) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        done(true);
      }, function () { fallbackCopy(url); });
    } else {
      fallbackCopy(url);
    }
  });
})();

/* Optional URL hash — the shareable view (Paul, Nov 12, 2026;
   full format documented at writeShareHash):
   #view=lat,lon,zoom opens at that view instead of fitting the
   whole trail; #base=code picks the background; #layers=… lists
   layers to switch on (a token prefixed with "-" switches that
   layer OFF); #types=… does the same for the asset-type toggles
   (uppercase codes). A token not listed leaves that toggle as
   the preset left it, so old partial links still work. */
var requestedView = null;
(function applyHash() {
  var hash = location.hash || "";
  var vm = /view=([-\d.]+),([-\d.]+),(\d+(?:\.\d+)?)/.exec(hash);
  if (vm) {
    requestedView = [parseFloat(vm[1]), parseFloat(vm[2])];
    requestedView.push(parseFloat(vm[3]));
  }
  var bm = /base=([a-z0-9\-]+)/.exec(hash);
  if (bm) {
    var baseDef = baseByCode(bm[1]);
    if (baseDef) setBase(baseDef.name);
  }
  var m = /layers=([a-z,\-]+)/.exec(hash);
  var wanted = [], unwanted = [];
  if (m) {
    m[1].split(",").forEach(function (tok) {
      if (tok.charAt(0) === "-") unwanted.push(tok.slice(1));
      else if (tok) wanted.push(tok);
    });
    LAYERS.forEach(function (def) {
      if (def.enabled === false || !def.box) return;
      if (unwanted.indexOf(def.id) >= 0) {
        def.box.checked = false;
        if (def.layer) map.removeLayer(def.layer);
      } else if (wanted.indexOf(def.id) >= 0 && !def.box.checked) {
        def.box.checked = true;
        ensureLayer(def, false);
      }
    });
  }
  var tm = /types=([A-Z,\-]+)/.exec(hash);
  if (tm) {
    tm[1].split(",").forEach(function (tok) {
      var off = tok.charAt(0) === "-";
      var code = off ? tok.slice(1) : tok;
      if (!code) return;
      var known = false;
      ASSET_TYPE_TOGGLES.forEach(function (t) {
        if (t[0] === code) known = true;
      });
      if (!known) return;
      assetTypeOn[code] = !off;
      var tbox = assetTypeBoxes[code];
      if (tbox) tbox.checked = !off;
      var sub = assetsTypeLayers[code];
      var def = layerById("assets");
      /* If the assets layer has not built yet, the build reads
         assetTypeOn and picks this up; nothing more to do here. */
      if (!sub || !def || !def.layer) return;
      if (!off) def.layer.addLayer(sub);
      else def.layer.removeLayer(sub);
    });
  }
  /* Adoption segment ends: an explicit hash token for them (on or
     off) wins. Otherwise their initial state is derived from the
     Adopted sections state as the hash leaves it — the same
     one-time derivation the panel builder applied at build. */
  var b = layerById("boundaries"), s = layerById("stretches");
  if (b && b.box && s && s.box &&
      wanted.indexOf("boundaries") < 0 &&
      unwanted.indexOf("boundaries") < 0) {
    b.box.checked = !!s.box.checked;
    if (b.box.checked) { ensureLayer(b, false); }
    else if (b.layer) { map.removeLayer(b.layer); }
  }
  /* The link is applied: the live writer may now record state
     without clobbering it. Normalize the hash to the full
     canonical form so Copy link works before any interaction. */
  shareHashReady = true;
  writeShareHash();
})();

function ensureLayer(def, announce) {
  if (def.enabled === false) return;
  if (def.layer) {
    def.layer.addTo(map);
    if (def.gate) def.gate();
    return;
  }
  if (def.loading) return;
  def.loading = true;
  if (def.noFetch) {
    /* Built from live objects, not a file (the Tree height
       overlay is two tile layers, not GeoJSON). */
    def.layer = def.build(null);
    if (def.box && def.box.checked) def.layer.addTo(map);
    def.loading = false;
    if (def.errEl) def.errEl.hidden = true;
    setStatus("");
    return;
  }
  if (announce) setStatus("Loading " + def.label + "…");
  fetch(def.file)
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (gj) {
      def.layer = def.build(gj);
      if (def.box && def.box.checked) def.layer.addTo(map);
      if (def.gate) def.gate();
      if (def.id === "trail") {
        if (requestedView) {
          map.setView([requestedView[0], requestedView[1]],
                      requestedView[2]);
        } else {
          /* Pad generously (UX P1): the east terminus label reaches
             ~90 px past its anchor and was clipped at the viewport
             edge; cap the opening zoom at 10. */
          try {
            map.fitBounds(def.layer.getBounds().pad(0.07), {
              paddingTopRight: [100, 20], maxZoom: 10,
            });
          } catch (e) {}
        }
        def.layer.bringToFront();
      }
      def.loading = false;
      if (def.errEl) def.errEl.hidden = true;
      setStatus("");
    })
    .catch(function (err) {
      def.loading = false;
      if (def.missingOk) {
        def.layer = L.layerGroup();
        if (def.box && def.box.checked) def.layer.addTo(map);
        setStatus("");
      } else {
        /* Load errors surface at the toggle that failed (UX P9),
           not in a status line under the panel. */
        if (def.errEl) {
          def.errEl.textContent = "Could not load " + def.label +
            " (" + err.message + ").";
          def.errEl.hidden = false;
        }
        setStatus("");
        if (def.box) def.box.checked = false;
      }
    });
}

/* Draw order, re-asserted on every layer add (layers load
   asynchronously): parcels stay at the back; the official line sits
   above them; adopted stretches above the line; the gap above the
   stretches; boundary ticks and chapter ends uppermost. */
function layerById(id) {
  for (var i = 0; i < LAYERS.length; i++) {
    if (LAYERS[i].id === id) return LAYERS[i];
  }
  return null;
}

/* (The pre-Nov 11 syncBoundaries() mirror — segment ends slaved
   to the Adopted sections toggle — is gone. The ends have their
   own "Adoption segment ends" checkbox now; their initial state
   is derived once from the sections state in the panel builder /
   applyHash, and nothing re-syncs them after load.) */
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
    /* Stacking, back → front (§2.12): the reservation polygon
       first (it is the largest context fill and must sit under
       everything, parcels included), then parcels, access
       context, roads, the official trail line, the ADOPTED
       SECTIONS on top of the trail line (Paul, Nov 10, 2026 —
       the amber highlight must read as lying over the green),
       the gap, boundary ticks and chapter ends, mile markers
       with the ticks, then Places, trail alerts and asset pins
       uppermost. */
    ["leechlake", "parcels", "logedw", "logfim", "logcass", "easements", "access",
     "roads", "nctasheets", "trail",
     "stretches", "gaps",
     "boundaries", "termini", "milemarkers", "chainage", "contours",
     "places",
     "alerts", "chapterplaces", "assets"].forEach(function (id) {
      var d = layerById(id);
      if (!d || !d.layer || !map.hasLayer(d.layer)) return;
      if (d.layer.bringToFront) { d.layer.bringToFront(); return; }
      if (d.layer.eachLayer) {
        d.layer.eachLayer(function (l) {
          if (l.bringToFront) l.bringToFront();
        });
      }
    });
    /* The selection highlight rides above everything else. */
    if (selectionHalo && map.hasLayer(selectionHalo)) {
      selectionHalo.eachLayer(function (l) {
        if (l.bringToFront) l.bringToFront();
      });
    }
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

/* ------------------------------------------------------------ legend
   Generated from the same style constants the layers draw with —
   the v3 legend was hand-copied strings and silently drifted (it
   advertised a deleted layer and the old invisible roads grey).
   The same rows feed the corner card and the print-only legend. */

function legendHtml() {
  var rows = [];
  function add(swatch, text) {
    rows.push("<div class='row'>" + swatch + "<span>" + text + "</span></div>");
  }
  function line(color, dashed) {
    return "<span class='swatch" + (dashed ? " dashed" : "") +
      "' style='border-top-color:" + color + "'></span>";
  }
  function bar(color, wide) {
    return "<span class='swatch bar" + (wide ? " wide" : "") +
      "' style='background:" + color + "'></span>";
  }
  function pin(color) {
    return "<span class='swatch pin' style='background:" +
      color + "'></span>";
  }
  add("", "<strong>NCTA Trail</strong>");
  add(line(CHAPTER_COLORS.ITM), "Itasca Moraine Chapter — off-road");
  add(line(CHAPTER_COLORS.ITM, true), "Itasca Moraine Chapter — on-road");
  add(line(CHAPTER_COLORS.LLC), "Laurentian Lakes Chapter — off-road");
  add(line(CHAPTER_COLORS.LLC, true), "Laurentian Lakes Chapter — on-road");
  add("", "<strong>Chapter sections</strong>");
  add(line(STRETCH_STYLE.color), "Adopted section");
  add(line(GAP_CORE_STYLE.color, true), "Adoption gap");
  add(bar(COLORS.tick),
    "Section boundary — bar across the line (Adoption segment ends)");
  add(bar(CHAPTER_COLORS.ITM, true),
    "Chapter boundary — longer bar across the line (Itasca Moraine terminus)");
  /* The Access points rows are gone with their layer (v3); the
     crossings live in Find now. */
  add("", "<strong>Mileage</strong>");
  add(pin(COLORS.tick),
    "Mile marker — whole mile (NCTA)");
  add("<span class='swatch num'>187</span>",
    "NCTA mile number");
  add("<span class='swatch num'>30</span>",
    "— miles from the west end (chapter chainage)");
  add("", "<strong>Non-road access</strong>");
  Object.keys(ACCESS_STYLES).forEach(function (k) {
    var s = ACCESS_STYLES[k];
    add(line(s.color, !!s.dashArray), s.label);
  });
  add("", "<strong>Roads</strong>");
  ["A", "B", "C", "F"].forEach(function (cls) {
    var s = ROAD_CLASS_STYLES[cls];
    add(line(s.color), s.short);
  });
  add("", "<strong>Public parcels</strong>");
  add("<span class='swatch fill' style='background:#fdbb84'></span>",
    "Parcel the trail crosses");
  add("<span class='swatch fill' style='background:#e7e1c3'></span>",
    "Adjoining parcel (corridor ring)");
  add(pin(COLORS.assetPin), "Asset pin (photo inventory)");
  add("", "<strong>Trail alerts</strong>");
  add("<span class='swatch alert'></span>",
    "Trail alert — closure, storm damage, reroute (NCTA)");
  add("", "<strong>Chapter places</strong>");
  add("<span class='swatch chapterdisc'>C</span>",
    "Chapter place — the chapter's own record (C camping, " +
    "W water, P parking, S shelter)");
  add("<span class='swatch chapterdisc closed'>C</span>",
    "Chapter place — CLOSED");
  add("", "<strong>The land</strong>");
  add("<span class='swatch fill' style='background:#64af5a'></span>",
    "Tree height — how tall the trees are (overlay, over any " +
    "background; white is open ground)");
  add(line("#8a6d1a"), "Height lines — every 5 m");
  add("<span class='swatch fill' style='background:#d97706'></span>",
    "Cass timber sale — year is the sale year (no expiry in the source)");
  add("<span class='swatch fill' style='background:#6b8e23'></span>",
    "Cass forest stand — inventory, not a sale");
  add("<span class='swatch fill' style='background:#64748b'></span>",
    "Chippewa NF timber sale — project area");
  return rows.join("");
}

(function buildLegend() {
  var html = legendHtml();
  var el = document.getElementById("legend");
  if (el) el.innerHTML = html;
  var printEl = document.getElementById("legend-print-body");
  if (printEl) printEl.innerHTML = html;
})();

/* Print header date stamp (DESIGN §6). */
(function printDate() {
  var el = document.getElementById("print-date");
  if (el) {
    el.textContent = " · " + new Date().toLocaleDateString("en-US", {
      year: "numeric", month: "long", day: "numeric",
    });
  }
})();

/* ---------------------------------------------------------- corner UI
   The panel's reference material (data sources + legend) lives
   behind two buttons fixed over the map's bottom-left corner, above
   the scale control; the Leaflet attribution (bottom-right) is
   separate and stays visible. Cards start closed; opening one
   closes the other (UX P2 — they used to stack two 55 vh cards
   over the map's southwest corner). */
(function cornerUi() {
  var ui = document.getElementById("corner-ui");
  if (!ui) return;
  L.DomEvent.disableClickPropagation(ui);
  L.DomEvent.disableScrollPropagation(ui);
  var pairs = [];
  function wire(btnId, cardId) {
    var btn = document.getElementById(btnId);
    var card = document.getElementById(cardId);
    if (!btn || !card) return;
    var pair = { btn: btn, card: card };
    pairs.push(pair);
    btn.addEventListener("click", function () {
      var open = card.hidden;
      pairs.forEach(function (p) {
        var on = p === pair ? open : false;
        p.card.hidden = !on;
        p.btn.setAttribute("aria-pressed", on ? "true" : "false");
        p.btn.classList.toggle("active", on);
      });
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
   layer here. v4: SECTION results feed the selection model (the
   inspector + a fitBounds, no point-zoom popup); other results
   keep the highlight marker + popup. Results are a real combobox:
   arrow keys move an active row, Enter selects through the same
   path as a click. */
var gazFeatures = null;
var gazLoading = false;
var gazCallbacks = [];
var gazMarker = null;

function gazLoad(done) {
  if (gazFeatures) { if (done) done(); return; }
  if (done) gazCallbacks.push(done);
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
      var cbs = gazCallbacks;
      gazCallbacks = [];
      cbs.forEach(function (cb) { cb(); });
      var hint = document.getElementById("gaz-hint");
      if (hint) {
        hint.textContent = gazFeatures.length +
          " places: sections, crossings, parking, camping, water. " +
          "Type a place, section, or crossing.";
      }
    })
    .catch(function () {
      gazLoading = false;
      gazCallbacks = [];
      setStatus("Could not load the Find index.");
    });
}

function gazSearch(q) {
  var tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length || !gazFeatures) return [];
  return gazFeatures.filter(function (f) {
    var hay = (f.properties.search_text || "").toLowerCase();
    return tokens.every(function (t) { return hay.indexOf(t) >= 0; });
  });
}

function gazContents(sectionName) {
  var byKind = {};
  if (!gazFeatures) return byKind;
  gazFeatures.forEach(function (f) {
    var p = f.properties;
    if (p.kind === "Section") return;
    var inside = p.section === sectionName ||
      (p.sections && p.sections.indexOf(sectionName) >= 0);
    if (!inside) return;
    (byKind[p.kind] = byKind[p.kind] || []).push(f);
  });
  return byKind;
}

/* Gazetteer provenance (Paul, Nov 12, 2026): every point names
   where it came from, so a reader who wants to edit a campsite
   knows whether it is the chapter's record or someone else's
   (NCTA, or the chapter's own crossings / boundary / tracker).
   The chapter-source points route to the chapter card instead. */
var GAZ_SOURCE_LABELS = {
  "ncta-points": "North Country Trail Association",
  "access-points": "Itasca Moraine Chapter — trail crossings",
  "boundaries": "Itasca Moraine Chapter — boundary",
  "tracker": "Itasca Moraine Chapter — tracker",
};
function gazPopupHtml(f) {
  var p = f.properties;
  /* A chapter place selected through Find or What's here gets
     its chapter card, not the NCTA waypoint card. */
  if (p.source === "chapter") return chapterPopupHtml(f);
  var rows = [
    ["Kind", p.kind],
    ["Chapter tracker mile",
      p.nct_mile != null ? p.nct_mile : null],
    ["From the west end",
      p.from_west_mi != null ? p.from_west_mi + " mi along the trail" : null],
    ["Source", GAZ_SOURCE_LABELS[p.source] || p.source],
  ];
  if (p.off_chain) {
    rows.push(["Position", "Off the depicted chapter chain — nearest " +
      "depicted point ≈ " + (p.snap_m / 1000).toFixed(1) + " km"]);
  }
  rows.push(["Description", p.description]);
  var html = "<h3>" + (esc(p.name) || "Place") + "</h3>" + kvTable(rows);
  /* The door (§5): the section is opened, not named in a row. A
     point on a section boundary names both — the first that
     resolves to a walk item is the door. */
  var door = null;
  if (p.section && walkByName[p.section]) door = p.section;
  else if (p.sections) {
    for (var i = 0; i < p.sections.length && !door; i++) {
      if (walkByName[p.sections[i]]) door = p.sections[i];
    }
  }
  var actions = "";
  if (door) {
    actions += "<button type='button' class='pop-door' data-section='" +
      esc(door) + "'>Open " + esc(door) + " record</button>";
  }
  actions += directionsHtml(f);
  if (actions) html += "<div class='pop-actions'>" + actions + "</div>";
  return html;
}

/* Non-section results: fly, highlight, popup (unchanged role). */
function gazSelect(f) {
  var c = f.geometry.coordinates;
  var latlng = L.latLng(c[1], c[0]);
  map.flyTo(latlng, Math.max(map.getZoom(), 14), { duration: 0.8 });
  if (gazMarker) map.removeLayer(gazMarker);
  gazMarker = L.circleMarker(latlng, {
    radius: 10, color: COLORS.gap, weight: 3,
    fillColor: "#fc8d59", fillOpacity: 0.55,
  }).addTo(map);
  bindPop(gazMarker, gazPopupHtml(f));
  window.setTimeout(function () { gazMarker.openPopup(); }, 850);
}

/* Section results: select into the inspector and fit the section's
   shape — no z14 point-zoom, no popup (UX Part 1). */
function gazSelectSection(f) {
  var name = f.properties.name;
  var item = walkByName[name];
  if (!item) { gazSelect(f); return; }
  /* Selecting a section turns its layer on if it was off — the
     record without the line makes no sense. */
  var defId = item.type === "gap" ? "gaps" : "stretches";
  var def = layerById(defId);
  if (def && def.box && !def.box.checked) {
    def.box.checked = true;
    ensureLayer(def, false);
    /* Adoption segment ends are NOT dragged along — they answer
       only to their own toggle (Nov 11, 2026). */
  }
  selectSection(item, "find");
  zoomToSelection();
}

var KIND_DOTS = {
  "Section": COLORS.adopted,
  "Section boundary": COLORS.tick,
  "Chapter end": COLORS.trailDeep,
  "Parking": "#0570b0",
  "Camping": COLORS.trail,
  "Water": "#22a7c6",
  "Shelter": "#8c510a",
  "POI": "#8856a7",
  "Road crossing": "#888888",
  "Trail crossing": "#888888",
};

function gazResultSub(p) {
  var bits = [p.kind];
  if (p.kind === "Section") {
    if (p.nct_mile_start != null && p.nct_mile_end != null) {
      bits.push("Tracker miles " + p.nct_mile_start + "–" +
        p.nct_mile_end);
    } else if (p.nct_mile != null) {
      bits.push("Tracker miles " + p.nct_mile);
    }
    if (p.length_mi != null) bits.push(p.length_mi + " mi");
  } else {
    if (p.nct_mile != null) bits.push("Tracker miles " + p.nct_mile);
    else if (p.off_chain) bits.push("off-chain");
    if (p.section) bits.push("in " + p.section);
    if (p.source === "chapter") {
      bits.push("Chapter record");
      if (p.status === "closed") bits.push("CLOSED");
    }
  }
  return bits.join(" · ");
}

(function gazetteerUi() {
  var input = document.getElementById("gaz-search");
  var box = document.getElementById("gaz-results");
  if (!input || !box) return;
  var current = [];       /* features behind the visible rows */
  var activeIdx = -1;
  var debounce = null;

  function hide() {
    box.hidden = true;
    box.innerHTML = "";
    current = [];
    activeIdx = -1;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }
  function setActive(i) {
    activeIdx = i;
    var rows = box.querySelectorAll(".gaz-result");
    rows.forEach(function (r, j) {
      r.classList.toggle("active", j === i);
      r.setAttribute("aria-selected", j === i ? "true" : "false");
    });
    if (i >= 0 && rows[i]) {
      input.setAttribute("aria-activedescendant", rows[i].id);
      rows[i].scrollIntoView({ block: "nearest" });
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  }
  function choose(f) {
    hide();
    if (f.properties.kind === "Section") gazSelectSection(f);
    else gazSelect(f);
  }
  function render() {
    var q = input.value.trim();
    if (!q) { hide(); return; }
    if (!gazFeatures) {
      box.innerHTML = "<div class='gaz-nomatch'>Loading the " +
        "index…</div>";
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
      return;
    }
    var results = gazSearch(q);
    current = results.slice(0, 8);
    activeIdx = -1;
    if (!results.length) {
      box.innerHTML = "<div class='gaz-nomatch'>No matches for " +
        "&#8220;" + (esc(q) || "") + "&#8221; — try a section " +
        "(Chip-3), a road, or a lake.</div>";
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
      return;
    }
    box.innerHTML = "";
    current.forEach(function (f, i) {
      var p = f.properties;
      var b = document.createElement("button");
      b.type = "button";
      b.className = "gaz-result";
      b.id = "gaz-opt-" + i;
      b.setAttribute("role", "option");
      b.setAttribute("aria-selected", "false");
      b.innerHTML = "<span class='gaz-name'>" +
        "<span class='gaz-dot' style='background:" +
        (KIND_DOTS[p.kind] || "#888888") + "'></span>" +
        (esc(p.name) || "Place") + "</span>" +
        "<span class='gaz-sub'>" + esc(gazResultSub(p)) + "</span>";
      b.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        choose(f);
      });
      b.addEventListener("mousemove", function () {
        if (activeIdx !== i) setActive(i);
      });
      box.appendChild(b);
    });
    if (results.length > current.length) {
      var foot = document.createElement("div");
      foot.className = "gaz-footer";
      foot.textContent = results.length +
        " matches — keep typing to narrow.";
      box.appendChild(foot);
    }
    box.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }
  input.addEventListener("focus", function () { gazLoad(render); });
  input.addEventListener("input", function () {
    if (debounce) window.clearTimeout(debounce);
    debounce = window.setTimeout(function () { gazLoad(render); }, 120);
  });
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      if (box.hidden || !current.length) return;
      ev.preventDefault();
      var d = ev.key === "ArrowDown" ? 1 : -1;
      var n = activeIdx + d;
      if (n < 0) n = 0;
      if (n >= current.length) n = current.length - 1;
      setActive(n);
    } else if (ev.key === "Enter") {
      if (!current.length) return;
      ev.preventDefault();
      choose(current[activeIdx >= 0 ? activeIdx : 0]);
    } else if (ev.key === "Escape") {
      hide();
    }
  });
  input.addEventListener("blur", function () {
    window.setTimeout(hide, 150);
  });
  /* "/" focuses Find from anywhere (UX P3). */
  document.addEventListener("keydown", function (e) {
    if (e.key !== "/") return;
    var t = document.activeElement;
    if (t && /INPUT|TEXTAREA|SELECT/.test(t.tagName)) return;
    e.preventDefault();
    input.focus();
  });
})();

/* Inspector starts in its empty state (prompt + gap callout). */
renderInspector();

/* Screen export — GeoPDF of the area you draw, with the layers you
 * have ticked (Nov 16, 2026).
 *
 * Runs on export.html alongside the normal viewer (app.js). The user
 * picks layers with the existing panel toggles, drags a rectangle on
 * the map, and downloads a GeoPDF. The export is rendered fresh from
 * the site's own data (data/*.geojson) and the site's street basemap
 * (OpenStreetMap tiles), in the viewer's colours — it does NOT
 * screenshot the live map, so it is identical every time and never
 * depends on the browser's tile cache or the canvas renderer.
 *
 * One basemap only: Streets (OSM). Aerial is a later step (Paul,
 * Nov 15, 2026). The rendered image is a Web Mercator rendering
 * georeferenced by its four corners (see geopdf-writer.js).
 *
 * Pixel sizes mirror scripts/export_geopdf.py: the script renders at
 * 100 dpi, so a line of W points is W*100/72 px and a marker radius
 * of R px prints the same in both. PX_PER_PT converts points to
 * canvas pixels; marker radii are used in px directly.
 */
(function () {
  "use strict";

  var PX_PER_PT = 100 / 72;
  var TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var OSM_ATTRIBUTION = "Basemap © OpenStreetMap contributors";
  var TARGET_PX = 1600;
  var EXPORT_DPI = 150;
  var MAX_TILES = 500;

  /* Paper sizes for the print dialog (Paul, Nov 17, 2026): [width,
     height] in inches, portrait. The dialog picks one, plus
     orientation and DPI; the canvas is rendered at exactly
     paper-inches x dpi pixels, so the GeoPDF page comes out at
     exactly the paper size (geopdf-writer.js sizes the page as
     px * 72 / dpi). */
  var PAPER_SIZES = {
    letter: [8.5, 11],
    legal: [8.5, 14],
    tabloid: [11, 17],
    a4: [8.27, 11.69],
    a3: [11.69, 16.54],
  };
  var PAPER_NAMES = {
    letter: "Letter", legal: "Legal", tabloid: "Tabloid",
    a4: "A4", a3: "A3",
  };

  function pxToLon(px, z) {
    return px / (256 * Math.pow(2, z)) * 360 - 180;
  }
  function pxToLat(py, z) {
    /* Inverse of latToPx: tileLat takes a tile-y, and py/256 is that. */
    return tileLat(py / 256, z);
  }

  /* Canvas pixels for a paper size + orientation at a DPI. */
  function paperPx(paper, orientation, dpi) {
    var dims = PAPER_SIZES[paper] || PAPER_SIZES.letter;
    var wIn = dims[0], hIn = dims[1];
    if (orientation === "landscape") {
      var t = wIn; wIn = hIn; hIn = t;
    }
    return [Math.round(wIn * dpi), Math.round(hIn * dpi)];
  }

  /* Expand lon/lat bounds [w, s, e, n] to the target width/height
     aspect, centred, in Web Mercator pixel space at zoom z — so the
     rendered map fills the paper exactly. Returns [w, s, e, n]. */
  function fitBoundsToAspect(w, s, e, n, aspect, z) {
    var x0 = lonToPx(w, z), x1 = lonToPx(e, z);
    var y0 = latToPx(n, z), y1 = latToPx(s, z);
    var cw = x1 - x0, ch = y1 - y0;
    if (cw / ch > aspect) {
      /* Too wide: grow the height (north/south). */
      var nh = cw / aspect, cy = (y0 + y1) / 2;
      y0 = cy - nh / 2; y1 = cy + nh / 2;
    } else {
      /* Too tall: grow the width (west/east). */
      var nw = ch * aspect, cx = (x0 + x1) / 2;
      x0 = cx - nw / 2; x1 = cx + nw / 2;
    }
    return [pxToLon(x0, z), pxToLat(y1, z), pxToLon(x1, z), pxToLat(y0, z)];
  }

  var COLORS = {
    trail: "#1a9850", trailDeep: "#14532d", neighbour: "#7e6a9e",
    slate: "#64748b", slateDark: "#37474f", adopted: "#e08214",
    gap: "#d7301f", gapDeep: "#b2182b", asset: "#e6550d",
    blue: "#4285f4", violet: "#7c3aed",
  };
  var ROAD_STYLES = {
    A: ["#616161", 2.75, null], B: ["#83837a", 2, null],
    C: ["#a9a396", 1.5, null], F: ["#8c510a", 1.75, null],
  };
  var ACCESS_STYLES = {
    state_park_trail_or_road: ["#35978f", 1.6, null],
    ohv_trail: ["#a63603", 1.75, "6 3 1.5 3"],
    state_trail: ["#2c7fb8", 2.25, null],
    snowmobile_trail: ["#8856a7", 1.4, "2 5"],
    hunter_walking_trail: ["#6e8b67", 1.4, "8 4"],
  };
  var ACCESS_DEFAULT = ["#666666", 1.75, null];
  var PLACE_GLYPHS = { Parking: "P", Camping: "C", Water: "W", Shelter: "S" };
  /* Land-polygon fills: [fill, edge, edgeWidthPt] (viewer washes). */
  var POLY_STYLES = {
    "chippewa-plan": ["#64748b", "#475569", 1.5],
    leechlake: ["#8e86c2", "#5e548e", 2],
    easements: ["#0d9488", "#0f766e", 1.5],
    logfim: ["#6b8e23", "#556b2f", 1],
    logcass: ["#d97706", "#92400e", 1.5],
    logedw: ["#64748b", "#475569", 1.5],
    loghubbard: ["#a16207", "#713f12", 1.5],
    logbecker: ["#15803d", "#14532d", 1.5],
    logclearwater: ["#1d4ed8", "#1e3a8a", 1.5],
    foresthealth: ["#dc2626", "#991b1b", 1.5],
  };
  var LAYER_FILES = {
    "chippewa-plan": "chippewa-plan-areas.geojson",
    leechlake: "leech-lake-reservation.geojson",
    easements: "easements.geojson",
    logfim: "logging-cass-fim-stands.geojson",
    logcass: "logging-cass-timber-sales.geojson",
    logedw: "logging-edw-timber-sale.geojson",
    loghubbard: "logging-hubbard-timber-sales.geojson",
    logbecker: "logging-becker-timber-sales.geojson",
    logclearwater: "logging-clearwater-timber-sales.geojson",
    foresthealth: "forest-health-2025.geojson",
    contours: "chm-contours.geojson",
    parcels: "parcels.geojson",
    nctasheets: "ncta-sheets.geojson",
    access: "access.geojson",
    roads: "roads.geojson",
    "trail-minnesota": "trail-minnesota.geojson",
    trail: "trail.geojson",
    stretches: "stretches.geojson",
    gaps: "gaps.geojson",
    "alerts-mn-lines": "trail-alert-lines-minnesota.geojson",
    milemarkers: "milemarkers.geojson",
    invasives: "invasive-sightings.geojson",
    alerts: "trail-alerts.geojson",
    streetview: "streetview.geojson",
    places: "gazetteer.geojson",
    chapterplaces: "chapter-places.geojson",
    assets: "assets.geojson",
    boundaries: "boundaries.geojson",
    termini: "boundaries.geojson",
    chainage: "chainage.geojson",
    "section-names": "stretches.geojson",
    /* Simple map (Paul, Nov 17, 2026): black linework on white.
       Lakes + towns + roads come from OSM (see
       scripts/build-simple-map-data.sh); parking from the
       gazetteer, trailheads from access-points. NOT in
       RENDER_ORDER — the simple branch draws them directly. */
    "simple-lakes": "simple-lakes.geojson",
    "simple-roads": "simple-roads.geojson",
    "simple-towns": "simple-towns.geojson",
    "simple-parking": "gazetteer.geojson",
    "simple-trailheads": "access-points.geojson",
    "simple-trail": "trail.geojson",
  };
  /* Draw order, bottom -> top (same as scripts/export_geopdf.py
     LAYERS and the viewer's assertDrawOrder). */
  var RENDER_ORDER = [
    "chippewa-plan", "leechlake", "easements", "logfim", "logcass",
    "logedw", "loghubbard", "logbecker", "logclearwater", "foresthealth",
    "contours", "parcels", "nctasheets", "access", "roads",
    "trail-minnesota", "trail", "stretches", "gaps", "alerts-mn-lines",
    "milemarkers", "invasives", "alerts", "streetview", "places",
    "chapterplaces", "assets", "boundaries", "termini", "chainage",
    "section-names",
  ];
  /* Legend rows, mirroring site/app.js legendHtml() and the script
     books. [kind, color, dash, text]; kind is line | bar | disc. */
  var LEGEND_ROWS = {
    trail: [
      ["line", COLORS.trail, null, "Itasca Moraine Chapter — off-road"],
      ["line", COLORS.trail, "2 7", "Itasca Moraine Chapter — on-road"],
      ["line", COLORS.neighbour, null, "Laurentian Lakes Chapter — off-road"],
      ["line", COLORS.neighbour, "2 7", "Laurentian Lakes Chapter — on-road"],
    ],
    stretches: [["line", COLORS.adopted, null, "Adopted section"]],
    gaps: [["line", COLORS.gap, "14 8", "Adoption gap"]],
    boundaries: [["bar", COLORS.slateDark, null,
      "Section boundary — bar across the line"]],
    termini: [["bar", COLORS.trail, null,
      "Chapter boundary (Itasca Moraine terminus)"]],
    milemarkers: [["disc", COLORS.slateDark, null,
      "Mile marker — whole mile (NCTA)"]],
    chainage: [["disc", COLORS.slateDark, null,
      "Chainage — miles from the west end"]],
    chapterplaces: [["disc", COLORS.trailDeep, null,
      "Camping — chapter campsite (C/W/P/S)"]],
    assets: [["disc", COLORS.asset, null, "Asset pin (photo inventory)"]],
    alerts: [["disc", COLORS.gap, null,
      "Trail alert — closure, damage, reroute (NCTA)"]],
    parcels: [
      ["fill", "#fdbb84", null, "Parcel the trail crosses"],
      ["fill", "#e7e1c3", null, "Adjoining parcel"],
    ],
    roads: [["line", "#616161", null, "Road"]],
    access: [["line", "#666666", null, "Non-road access"]],
    easements: [["fill", "#0d9488", null, "Conservation easement"]],
    leechlake: [["fill", "#8e86c2", null, "Leech Lake Reservation"]],
  };
  var LEGEND_ORDER = ["trail", "stretches", "gaps", "boundaries",
    "termini", "milemarkers", "chainage", "chapterplaces", "assets",
    "alerts", "parcels", "roads", "access", "easements", "leechlake"];

  /* ---------------------------------------------------------- state */
  var tileCache = new Map();
  var gjCache = new Map();
  var drawing = false;
  var startLatLng = null;
  var rectLayer = null;
  var exportBounds = null;

  /* -------------------------------------------------- slippy helpers */
  function lonToPx(lon, z) {
    return (lon + 180) / 360 * 256 * Math.pow(2, z);
  }
  function latToPx(lat, z) {
    var s = Math.sin(lat * Math.PI / 180);
    return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) *
      256 * Math.pow(2, z);
  }
  function tileLat(ty, z) {
    var n = Math.PI * (1 - 2 * ty / Math.pow(2, z));
    return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  }
  function chooseZoom(w, s, e, n, targetPx) {
    var latRef = (s + n) / 2;
    var widthM = (e - w) * 111320 * Math.cos(latRef * Math.PI / 180);
    var targetRes = widthM / targetPx;
    var best = 10, bestErr = Infinity;
    for (var z = 9; z <= 17; z++) {
      var res = 156543.03392 * Math.cos(latRef * Math.PI / 180) /
        Math.pow(2, z);
      var err = Math.abs(Math.log(res / targetRes));
      if (err < bestErr) { bestErr = err; best = z; }
    }
    return Math.max(10, Math.min(16, best));
  }

  /* ------------------------------------------------------- fetching */
  function fetchTile(z, x, y) {
    var key = z + "/" + x + "/" + y;
    if (tileCache.has(key)) return Promise.resolve(tileCache.get(key));
    var url = TILE_URL.replace("{z}", z).replace("{x}", x)
      .replace("{y}", y);
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("tile " + key + ": HTTP " + r.status);
      return r.blob();
    }).then(function (blob) {
      return new Promise(function (resolve, reject) {
        var objUrl = URL.createObjectURL(blob);
        var img = new Image();
        img.onload = function () {
          tileCache.set(key, img);
          resolve(img);
        };
        img.onerror = function () {
          URL.revokeObjectURL(objUrl);
          reject(new Error("tile " + key + ": decode failed"));
        };
        img.src = objUrl;
      });
    });
  }
  function fetchGeoJSON(file) {
    if (gjCache.has(file)) return Promise.resolve(gjCache.get(file));
    return fetch("data/" + file).then(function (r) {
      if (!r.ok) throw new Error("data/" + file + ": HTTP " + r.status);
      return r.json();
    }).then(function (gj) {
      gjCache.set(file, gj);
      return gj;
    });
  }

  /* ------------------------------------------------- geometry helpers */
  function walkGeom(geom, cb) {
    if (!geom) return;
    var t = geom.type;
    if (t === "GeometryCollection") {
      /* e.g. West Crooked Lake arrives as Polygon + LineString. */
      (geom.geometries || []).forEach(function (g) { walkGeom(g, cb); });
    }
    else if (t === "Point") cb("point", geom.coordinates);
    else if (t === "MultiPoint") {
      geom.coordinates.forEach(function (c) { cb("point", c); });
    } else if (t === "LineString") cb("line", geom.coordinates);
    else if (t === "MultiLineString") {
      geom.coordinates.forEach(function (c) { cb("line", c); });
    } else if (t === "Polygon") cb("poly", geom.coordinates);
    else if (t === "MultiPolygon") {
      geom.coordinates.forEach(function (c) { cb("poly", c); });
    }
  }
  function isOnRoad(p) {
    return p.trail_stat === "NCT (on-road)" ||
      p.trail_type === "Public Road";
  }
  function lineLengthM(coords) {
    var total = 0;
    for (var i = 0; i + 1 < coords.length; i++) {
      var lat = (coords[i][1] + coords[i + 1][1]) / 2 * Math.PI / 180;
      var dx = (coords[i + 1][0] - coords[i][0]) * 111320 * Math.cos(lat);
      var dy = (coords[i + 1][1] - coords[i][1]) * 110540;
      total += Math.sqrt(dx * dx + dy * dy);
    }
    return total;
  }
  /* Bounding box of a GeoJSON geometry, [minLon, minLat, maxLon,
     maxLat], or null. Used to skip features outside the sheet. */
  function geomBBox(geom) {
    if (!geom || !geom.coordinates) return null;
    var b = [Infinity, Infinity, -Infinity, -Infinity];
    var found = false;
    (function walk(c) {
      if (typeof c[0] === "number") {
        found = true;
        if (c[0] < b[0]) b[0] = c[0];
        if (c[0] > b[2]) b[2] = c[0];
        if (c[1] < b[1]) b[1] = c[1];
        if (c[1] > b[3]) b[3] = c[1];
      } else {
        for (var i = 0; i < c.length; i++) walk(c[i]);
      }
    })(geom.coordinates);
    return found ? b : null;
  }
  /* True when the geometry's bbox overlaps the view (lon/lat, already
     expanded by a margin). A long straight line crossing the sheet
     still overlaps even if no vertex falls inside it. */
  function geomInView(geom, view) {
    if (!view) return true;
    var b = geomBBox(geom);
    if (!b) return false;
    return b[2] >= view[0] && b[0] <= view[2] &&
      b[3] >= view[1] && b[1] <= view[3];
  }

  function dashArray(spec) {
    if (!spec) return [];
    return spec.split(" ").map(function (v) {
      return parseFloat(v) * PX_PER_PT;
    });
  }

  /* --------------------------------------------------- canvas drawing */
  function strokeCoords(ctx, coords, proj, color, widthPt, dash) {
    ctx.beginPath();
    for (var i = 0; i < coords.length; i++) {
      var x = proj.x(coords[i][0]), y = proj.y(coords[i][1]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = widthPt * PX_PER_PT;
    ctx.setLineDash(dashArray(dash));
    ctx.stroke();
    ctx.setLineDash([]);
  }
  function fillPoly(ctx, rings, proj, fill, edge, edgeWidthPt, alpha) {
    ctx.beginPath();
    rings.forEach(function (ring) {
      ring.forEach(function (c, i) {
        var x = proj.x(c[0]), y = proj.y(c[1]);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.closePath();
    });
    if (fill) {
      ctx.save();
      ctx.globalAlpha = (alpha == null ? 1 : alpha);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.restore();
    }
    if (edge) {
      ctx.strokeStyle = edge;
      ctx.lineWidth = edgeWidthPt * PX_PER_PT;
      ctx.stroke();
    }
  }
  function disc(ctx, x, y, r, fill, edge) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    if (edge) {
      ctx.strokeStyle = edge;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }
  function label(ctx, x, y, text, sizePt, color, bold) {
    ctx.font = (bold ? "bold " : "") +
      Math.round(sizePt * PX_PER_PT) + "px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "white";
    ctx.lineJoin = "round";
    ctx.strokeText(text, x, y);
    ctx.fillStyle = color;
    ctx.fillText(text, x, y);
  }

  /* One layer's features -> canvas. env collects legend flags
     (drawn lengths in metres per trail class; gap when a gap was
     drawn) and the asset-type filter. Returns features drawn. */
  function drawLayer(ctx, id, gj, proj, env) {
    /* Draw only features whose bbox overlaps the sheet: the files
       hold the whole chapter (and, for trail-minnesota, the whole
       state), so drawing everything would be slow AND would corrupt
       the legend flags (lengths would count off-sheet trail). */
    var feats = (gj.features || []).filter(function (f) {
      return geomInView(f.geometry, proj.view);
    });
    var n = 0;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (POLY_STYLES[id]) {
      var st = POLY_STYLES[id];
      feats.forEach(function (f) {
        walkGeom(f.geometry, function (kind, coords) {
          if (kind === "poly") {
            fillPoly(ctx, coords, proj, st[0], st[1], st[2], 0.35);
            n++;
          }
        });
      });
      return n;
    }

    switch (id) {
      case "contours":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, "#8a6d1a", 1, null);
              n++;
            }
          });
        });
        return n;
      case "parcels":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "poly") return;
            var crossed = f.properties.corridor === "crossed";
            fillPoly(ctx, coords, proj,
              crossed ? "#fdbb84" : "#e7e1c3",
              crossed ? "#b35806" : "#a89a5b", 0.8, 0.5);
            n++;
          });
        });
        return n;
      case "nctasheets":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, "#8a6d1a", 1.5, "6 4");
              n++;
            } else if (kind === "poly") {
              var xs = coords[0].map(function (c) { return proj.x(c[0]); });
              var ys = coords[0].map(function (c) { return proj.y(c[1]); });
              label(ctx,
                xs.reduce(function (a, b) { return a + b; }, 0) / xs.length,
                ys.reduce(function (a, b) { return a + b; }, 0) / ys.length,
                String(f.properties.sheet || ""), 9, "#8a6d1a", false);
              n++;
            }
          });
        });
        return n;
      case "access": {
        feats.forEach(function (f) {
          var s = ACCESS_STYLES[f.properties.source_type] || ACCESS_DEFAULT;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, s[0], s[1], s[2]);
              n++;
            }
          });
        });
        return n;
      }
      case "roads": {
        feats.forEach(function (f) {
          var s = ROAD_STYLES[f.properties.road_class || "C"] ||
            ROAD_STYLES.C;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, s[0], s[1], s[2]);
              n++;
            }
          });
        });
        return n;
      }
      case "trail-minnesota":
        ctx.save();
        ctx.globalAlpha = 0.75;
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, COLORS.slate, 2,
                isOnRoad(f.properties) ? "2 7" : null);
              n++;
            }
          });
        });
        ctx.restore();
        return n;
      case "trail":
        feats.forEach(function (f) {
          if (f.properties.chapter !== "ITM") return;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, "#ffffff", 7, null);
            }
          });
        });
        feats.forEach(function (f) {
          var p = f.properties;
          var llc = p.chapter === "LLC";
          var onRoad = isOnRoad(p);
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "line") return;
            var len = lineLengthM(coords);
            if (llc) {
              env.llcM += len;
              if (onRoad) env.llcOnroadM += len;
            } else if (onRoad) env.onroadM += len;
            else env.itmM += len;
            strokeCoords(ctx, coords, proj,
              llc ? COLORS.neighbour : COLORS.trail,
              llc ? 2.5 : 4, onRoad ? "2 7" : null);
            n++;
          });
        });
        return n;
      case "stretches":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, "#ffffff", 8.5, null);
            }
          });
        });
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, COLORS.adopted, 6, null);
              n++;
            }
          });
        });
        return n;
      case "gaps":
        if (feats.length) env.gap = true;
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, COLORS.gapDeep, 11, null);
            }
          });
        });
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, COLORS.gap, 5, "14 8");
              n++;
            }
          });
        });
        return n;
      case "alerts-mn-lines":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, COLORS.gap, 3, "6 4");
              n++;
            }
          });
        });
        return n;
      case "milemarkers":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            if (f.properties.index_ === "Index") {
              disc(ctx, x, y, 11, "#ffffff", "#ffffff");
              disc(ctx, x, y, 10, COLORS.slateDark, COLORS.slateDark);
              label(ctx, x, y, String(f.properties.label || ""),
                9, COLORS.slateDark, false);
            } else {
              disc(ctx, x, y, 4, COLORS.slateDark, COLORS.slateDark);
            }
            n++;
          });
        });
        return n;
      case "invasives":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            disc(ctx, x, y, 4, COLORS.violet, "#ffffff");
            n++;
          });
        });
        return n;
      case "alerts":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(Math.PI / 4);
            ctx.fillStyle = COLORS.gap;
            ctx.fillRect(-7, -7, 14, 14);
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1;
            ctx.strokeRect(-7, -7, 14, 14);
            ctx.restore();
            n++;
          });
        });
        return n;
      case "streetview":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            disc(ctx, x, y, 7, COLORS.blue, "#ffffff");
            n++;
          });
        });
        return n;
      case "places":
        feats.forEach(function (f) {
          if (f.properties.source === "chapter") return;
          var glyph = PLACE_GLYPHS[f.properties.kind];
          if (f.properties.kind !== "POI" && !glyph) return;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            if (f.properties.kind === "POI") {
              disc(ctx, x, y, 4, COLORS.slateDark, COLORS.slateDark);
            } else {
              disc(ctx, x, y, 7, "#ffffff", COLORS.slateDark);
              label(ctx, x, y, glyph, 8, COLORS.slateDark, false);
            }
            n++;
          });
        });
        return n;
      case "chapterplaces":
        feats.forEach(function (f) {
          var glyph = PLACE_GLYPHS[f.properties.kind];
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            if (glyph) {
              disc(ctx, x, y, 7, COLORS.trailDeep, "#ffffff");
              label(ctx, x, y, glyph, 8, "#ffffff", false);
            } else {
              disc(ctx, x, y, 4, COLORS.trailDeep, COLORS.trailDeep);
            }
            n++;
          });
        });
        return n;
      case "assets":
        feats.forEach(function (f) {
          if (env.assetTypes && !env.assetTypes.has(f.properties.type)) return;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            disc(ctx, x, y, 7, COLORS.asset, "#ffffff");
            n++;
          });
        });
        return n;
      case "boundaries":
      case "termini": {
        var terminiOnly = id === "termini";
        var kept = [];
        feats.forEach(function (f) {
          var p = f.properties;
          if (terminiOnly !== !!p.chapter_end) return;
          if (!terminiOnly && !p.tick) return;
          if (!p.tick) return;
          var xs = p.tick.map(function (c) { return proj.x(c[0]); });
          var ys = p.tick.map(function (c) { return proj.y(c[1]); });
          var mx = (xs[0] + xs[1]) / 2, my = (ys[0] + ys[1]) / 2;
          if (mx < -40 || my < -40 || mx > proj.W + 40 || my > proj.H + 40) return;
          kept.push({ xs: xs, ys: ys, mx: mx, my: my });
        });
        var passes = terminiOnly
          ? [[8, "#ffffff"], [4.5, COLORS.trail]]
          : [[5, "#ffffff"], [2.75, COLORS.slateDark]];
        passes.forEach(function (pass) {
          kept.forEach(function (t) {
            ctx.beginPath();
            ctx.moveTo(t.xs[0], t.ys[0]);
            ctx.lineTo(t.xs[1], t.ys[1]);
            ctx.strokeStyle = pass[1];
            ctx.lineWidth = pass[0] * PX_PER_PT;
            ctx.lineCap = "butt";
            ctx.stroke();
          });
        });
        ctx.lineCap = "round";
        if (terminiOnly) {
          kept.sort(function (a, b) { return a.mx - b.mx; });
          kept.forEach(function (t, i) {
            label(ctx, t.mx, t.my,
              "Itasca Moraine - " + (i === 0 ? "west end" : "east end"),
              11, COLORS.trailDeep, false);
          });
        }
        return kept.length;
      }
      case "chainage":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            if (f.properties.every10) {
              label(ctx, x, y, String(f.properties.miles_from_west || ""),
                11, COLORS.slateDark, false);
            } else {
              disc(ctx, x, y, 4, COLORS.slateDark, COLORS.slateDark);
            }
            n++;
          });
        });
        return n;
      case "section-names":
        feats.forEach(function (f) {
          var cx = null, cy = null;
          walkGeom(f.geometry, function (kind, coords) {
            if (cx !== null) return;
            if (kind === "poly") {
              var ring = coords[0];
              cx = ring.reduce(function (a, c) { return a + proj.x(c[0]); }, 0) / ring.length;
              cy = ring.reduce(function (a, c) { return a + proj.y(c[1]); }, 0) / ring.length;
            } else if (kind === "line") {
              var mid = coords[Math.floor(coords.length / 2)];
              cx = proj.x(mid[0]);
              cy = proj.y(mid[1]);
            }
          });
          if (cx === null) return;
          /* Skip names anchored within 6% of the sheet edge: a
             neighbouring section's name would print half off-page. */
          if (cx < proj.W * 0.06 || cx > proj.W * 0.94 ||
              cy < proj.H * 0.06 || cy > proj.H * 0.94) return;
          label(ctx, cx, cy, String(f.properties.name || ""), 10, "#000000", false);
          n++;
        });
        return n;
      /* ---- Simple map (Paul, Nov 17, 2026): black linework on
         white. Widths are points (scaled by PX_PER_PT); markers
         are sized in points too, so they hold up at 300/600 dpi. */
      case "simple-lakes":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "poly") {
              /* Outline only — no fill (the board member's ask). */
              fillPoly(ctx, coords, proj, null, "#000000", 1, null);
              n++;
            }
          });
        });
        return n;
      case "simple-roads":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, "#777777", 1.5, null);
              n++;
            }
          });
        });
        return n;
      case "simple-trail":
        feats.forEach(function (f) {
          walkGeom(f.geometry, function (kind, coords) {
            if (kind === "line") {
              strokeCoords(ctx, coords, proj, "#000000", 3, null);
              n++;
            }
          });
        });
        return n;
      case "simple-parking":
        feats.forEach(function (f) {
          if (f.properties.kind !== "Parking") return;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            disc(ctx, x, y, 7 * PX_PER_PT, "#000000", "#ffffff");
            label(ctx, x, y, "P", 8, "#ffffff", false);
            n++;
          });
        });
        return n;
      case "simple-trailheads":
        feats.forEach(function (f) {
          if (f.properties.kind !== "road") return;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -20 || y < -20 || x > proj.W + 20 || y > proj.H + 20) return;
            disc(ctx, x, y, 4 * PX_PER_PT, "#000000", "#ffffff");
            n++;
          });
        });
        return n;
      case "simple-towns": {
        var TOWN_PT = { city: 13, town: 12, village: 11, hamlet: 10 };
        feats.forEach(function (f) {
          var name = f.properties.name;
          if (!name) return;
          var size = TOWN_PT[f.properties.place] || 10;
          walkGeom(f.geometry, function (kind, coords) {
            if (kind !== "point") return;
            var x = proj.x(coords[0]), y = proj.y(coords[1]);
            if (x < -40 || y < -40 || x > proj.W + 40 || y > proj.H + 40) return;
            label(ctx, x, y, String(name), size, "#000000", false);
            n++;
          });
        });
        return n;
      }
      default:
        return 0;
    }
  }

  /* --------------------------------------------------------- legend */
  function legendRowsFor(drawnIds, env) {
    var rows = [];
    LEGEND_ORDER.forEach(function (lid) {
      if (drawnIds.indexOf(lid) < 0) return;
      if (lid === "trail") {
        var itm = env.itmM, onroad = env.onroadM;
        var llc = env.llcM - env.llcOnroadM, llcOn = env.llcOnroadM;
        var base = rows.length;
        if (itm > 100) rows.push(LEGEND_ROWS.trail[0]);
        if (onroad > 100) rows.push(LEGEND_ROWS.trail[1]);
        if (llc > 100) rows.push(LEGEND_ROWS.trail[2]);
        if (llcOn > 100) rows.push(LEGEND_ROWS.trail[3]);
        if (rows.length === base) rows.push(LEGEND_ROWS.trail[0]);
        return;
      }
      if (lid === "gaps" && !env.gap) return;
      (LEGEND_ROWS[lid] || []).forEach(function (r) { rows.push(r); });
    });
    return rows;
  }

  function drawLegend(ctx, rows, W, H) {
    if (!rows.length) return;
    var fs = Math.round(9 * PX_PER_PT);
    var charPx = 6.5;
    var swatchPx = 26, gapPx = 10, padPx = 12;
    var rowHPx = 17, titleHPx = 24;
    var maxChars = 0;
    rows.forEach(function (r) { maxChars = Math.max(maxChars, r[3].length); });
    var boxW = padPx * 2 + swatchPx + gapPx + Math.round(maxChars * charPx);
    var boxH = padPx * 2 + titleHPx + rows.length * rowHPx;
    var x0 = 14, y0 = H - 14 - boxH;
    ctx.save();
    ctx.globalAlpha = 0.92;
    ctx.fillStyle = "white";
    ctx.fillRect(x0, y0, boxW, boxH);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = "#666666";
    ctx.lineWidth = 1;
    ctx.strokeRect(x0, y0, boxW, boxH);
    ctx.fillStyle = "#000000";
    ctx.font = "bold " + Math.round(10 * PX_PER_PT) + "px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("Legend", x0 + padPx, y0 + padPx + 8);
    rows.forEach(function (row, i) {
      var cy = y0 + padPx + titleHPx + 8 + i * rowHPx + rowHPx / 2 - 4;
      var sx = x0 + padPx;
      var kind = row[0], color = row[1], dash = row[2];
      if (kind === "line") {
        ctx.beginPath();
        ctx.moveTo(sx, cy);
        ctx.lineTo(sx + swatchPx, cy);
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.setLineDash(dashArray(dash));
        ctx.stroke();
        ctx.setLineDash([]);
      } else if (kind === "bar" || kind === "fill") {
        ctx.fillStyle = color;
        ctx.fillRect(sx, cy - 5, swatchPx, 10);
        if (kind === "fill") {
          ctx.strokeStyle = "#666666";
          ctx.lineWidth = 0.5;
          ctx.strokeRect(sx, cy - 5, swatchPx, 10);
        }
      } else if (kind === "disc") {
        ctx.beginPath();
        ctx.arc(sx + swatchPx / 2, cy, 5.5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      }
      ctx.fillStyle = "#000000";
      ctx.font = fs + "px sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(row[3], sx + swatchPx + gapPx, cy);
    });
    ctx.restore();
  }

  function drawTitleFooter(ctx, title, subtitle, W, H) {
    ctx.save();
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.font = "bold " + Math.round(13 * PX_PER_PT) + "px sans-serif";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "white";
    ctx.lineJoin = "round";
    var tx = Math.round(W * 0.015), ty = Math.round(H * 0.015);
    ctx.strokeText(title, tx, ty);
    ctx.fillStyle = "#000000";
    ctx.fillText(title, tx, ty);
    if (subtitle) {
      ctx.font = Math.round(9.5 * PX_PER_PT) + "px sans-serif";
      var sy = ty + 22;
      ctx.strokeText(subtitle, tx, sy);
      ctx.fillStyle = "#000000";
      ctx.fillText(subtitle, tx, sy);
    }
    var today = new Date().toISOString().slice(0, 10);
    ctx.font = Math.round(7.5 * PX_PER_PT) + "px sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "bottom";
    var fx = Math.round(W * 0.985), fy = Math.round(H * 0.985);
    var foot = OSM_ATTRIBUTION + " · " + today;
    ctx.strokeText(foot, fx, fy);
    ctx.fillStyle = "#000000";
    ctx.fillText(foot, fx, fy);
    ctx.restore();
  }

  /* ------------------------------------------- render one export sheet */
  async function renderExport(bounds, layerIds, title, subtitle, onProgress, opts) {
    var w = bounds.getWest(), s = bounds.getSouth();
    var e = bounds.getEast(), n = bounds.getNorth();
    /* Paper path (print dialog, Paul Nov 17, 2026): opts.paper picks a
       paper size, opts.orientation portrait/landscape, opts.dpi the
       resolution. Without opts this is exactly the old behaviour — a
       bounds-shaped sheet, 1600 px long edge, 150 dpi. */
    var paper = opts && opts.paper && PAPER_SIZES[opts.paper];
    var dpi = (opts && opts.dpi) || EXPORT_DPI;
    var savedPxPerPt = PX_PER_PT;
    try {
    var zoom, W, H;
    if (paper) {
      var dims = paperPx(opts.paper, opts.orientation, dpi);
      W = dims[0]; H = dims[1];
      var targetPx = Math.max(W, H);
      zoom = chooseZoom(w, s, e, n, targetPx);
      var fit = fitBoundsToAspect(w, s, e, n, W / H, zoom);
      w = fit[0]; s = fit[1]; e = fit[2]; n = fit[3];
      zoom = chooseZoom(w, s, e, n, targetPx);
      /* Lines and type print at their true point sizes at this DPI. */
      PX_PER_PT = dpi / 72;
    } else {
      zoom = chooseZoom(w, s, e, n, TARGET_PX);
      W = TARGET_PX;
    }
    var x0 = lonToPx(w, zoom), x1 = lonToPx(e, zoom);
    var y0 = latToPx(n, zoom), y1 = latToPx(s, zoom);
    if (!paper) {
      H = Math.round(W * (y1 - y0) / (x1 - x0));
      if (H > 2600) {
        H = 2600;
        W = Math.round(H * (x1 - x0) / (y1 - y0));
      }
    }

    /* Simple map (Paul, Nov 17, 2026): black linework on a white
       page, using ONLY the dialog's checklist — it replaces the
       layers ticked in the panel for this print. */
    var simple = !!(opts && opts.simple);
    var simpleLayers = (opts && opts.simpleLayers) || {};
    function simpleOn(key) { return simpleLayers[key] !== false; }

    /* Basemap: OSM street tiles covering the area — skipped for a
       Simple map, which is black linework on a white page. */
    function tileList() {
      var list = [];
      var a0 = Math.floor(x0 / 256), a1 = Math.floor((x1 - 1) / 256);
      var b0 = Math.floor(y0 / 256), b1 = Math.floor((y1 - 1) / 256);
      for (var tx = a0; tx <= a1; tx++) {
        for (var ty = b0; ty <= b1; ty++) list.push([tx, ty]);
      }
      return list;
    }
    var tiles = simple ? [] : tileList();
    if (paper && !simple) {
      /* Step the basemap zoom down until the tile count fits the
         budget; the vector layers stay full-resolution, only the
         street backdrop softens. */
      while (tiles.length > MAX_TILES && zoom > 9) {
        zoom--;
        x0 = lonToPx(w, zoom); x1 = lonToPx(e, zoom);
        y0 = latToPx(n, zoom); y1 = latToPx(s, zoom);
        tiles = tileList();
      }
    }
    if (!simple && tiles.length > MAX_TILES) {
      throw new Error("area too large: needs " + tiles.length +
        " basemap tiles (max " + MAX_TILES + "); draw a smaller area");
    }
    var canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    var ctx = canvas.getContext("2d");
    var proj = {
      W: W, H: H,
      /* View for the feature pre-filter, margined so lines just
         outside the sheet still draw up to the edge. */
      view: [w - 0.02, s - 0.02, e + 0.02, n + 0.02],
      x: function (lon) { return (lonToPx(lon, zoom) - x0) / (x1 - x0) * W; },
      y: function (lat) { return (latToPx(lat, zoom) - y0) / (y1 - y0) * H; },
    };
    if (simple) {
      /* White page (a JPEG has no transparency — an unfilled
         canvas would print black). */
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, W, H);
    } else {
      if (onProgress) onProgress("Basemap: fetching " + tiles.length +
        " street tiles (zoom " + zoom + ")…");
      var BATCH = 6;
      for (var i = 0; i < tiles.length; i += BATCH) {
        var batch = tiles.slice(i, i + BATCH);
        var imgs = await Promise.all(batch.map(function (t) {
          return fetchTile(zoom, t[0], t[1]);
        }));
        imgs.forEach(function (img, j) {
          var txx = batch[j][0], tyy = batch[j][1];
          var tLonW = txx / Math.pow(2, zoom) * 360 - 180;
          var tLonE = (txx + 1) / Math.pow(2, zoom) * 360 - 180;
          var tLatN = tileLat(tyy, zoom), tLatS = tileLat(tyy + 1, zoom);
          var dx = proj.x(tLonW), dw = proj.x(tLonE) - dx;
          var dy = proj.y(tLatN), dh = proj.y(tLatS) - dy;
          ctx.drawImage(img, dx, dy, dw, dh);
        });
      }
    }

    /* Vectors, in the viewer's draw order. */
    var env = { itmM: 0, onroadM: 0, llcM: 0, llcOnroadM: 0, gap: false,
      assetTypes: enabledAssetTypes() };
    var drawnIds = [];
    var drawnCount = {};
    var simpleSkipped = [];
    if (simple) {
      /* Fixed order, bottom -> top: lakes, roads, trail, parking
         + trailheads, towns. A file that fails to load is skipped
         (the dialog greys it out first); roads fall back to the
         chapter's curated roads file when the OSM extract is
         missing. */
      var simplePlan = [
        ["lakes", "simple-lakes", null],
        ["roads", "simple-roads", "roads"],
        ["trail", "simple-trail", null],
        ["parking", "simple-parking", null],
        ["parking", "simple-trailheads", null],
        ["towns", "simple-towns", null],
      ];
      for (var s = 0; s < simplePlan.length; s++) {
        var sKey = simplePlan[s][0], sId = simplePlan[s][1],
            sFallback = simplePlan[s][2];
        if (!simpleOn(sKey)) continue;
        var sFile = LAYER_FILES[sId];
        if (!sFile) continue;
        if (onProgress) onProgress("Drawing " + sId + "…");
        var sGj = null;
        try {
          sGj = await fetchGeoJSON(sFile);
        } catch (sErr) {
          if (sFallback) {
            try { sGj = await fetchGeoJSON(LAYER_FILES[sFallback]); }
            catch (sErr2) { sGj = null; }
          }
        }
        if (!sGj) { simpleSkipped.push(sKey); continue; }
        var sCnt = drawLayer(ctx, sId, sGj, proj, env);
        if (sCnt > 0) {
          drawnIds.push(sId);
          drawnCount[sId] = sCnt;
        }
      }
    } else {
      for (var k = 0; k < RENDER_ORDER.length; k++) {
        var id = RENDER_ORDER[k];
        if (layerIds.indexOf(id) < 0) continue;
        var file = LAYER_FILES[id];
        if (!file) continue;
        if (onProgress) onProgress("Drawing " + id + "…");
        var gj = await fetchGeoJSON(file);
        var cnt = drawLayer(ctx, id, gj, proj, env);
        if (cnt > 0) {
          drawnIds.push(id);
          drawnCount[id] = cnt;
        }
      }
    }

    /* The legend and title stay off the printed map (Paul, Nov 16,
       2026 — the legend goes on a companion sheet, titles are
       added in other software). The export page's bounds-shaped
       path keeps them, as before. */
    if (!paper) {
      drawLegend(ctx, legendRowsFor(drawnIds, env), W, H);
      drawTitleFooter(ctx, title, subtitle, W, H);
    }
    return { canvas: canvas, bbox: [w, s, e, n], zoom: zoom,
      layers: drawnIds, counts: drawnCount,
      simpleSkipped: simpleSkipped };
    } finally {
      /* The paper path scales PX_PER_PT to the chosen DPI; restore it
         so a later bounds-shaped export renders as before. */
      PX_PER_PT = savedPxPerPt;
    }
  }

  /* ------------------------------------------- which layers are on? */
  function onLayerIds() {
    var ids = [];
    if (typeof LAYERS === "undefined") return ids;
    LAYERS.forEach(function (def) {
      var on = def.box ? def.box.checked : !!def.onByDefault;
      /* The Camping / Trail-alerts sub-toggles own their layers. */
      if (def.id === "chapterplaces" &&
          typeof campingBox !== "undefined" && campingBox) {
        on = campingBox.checked;
      }
      if (def.id === "alerts" &&
          typeof alertsBox !== "undefined" && alertsBox) {
        on = alertsBox.checked;
      }
      if (on) ids.push(def.id);
    });
    return ids;
  }
  function enabledAssetTypes() {
    if (typeof assetTypeBoxes === "undefined" || !assetTypeBoxes) return null;
    var enabled = [], anyOff = false, any = false;
    Object.keys(assetTypeBoxes).forEach(function (code) {
      var box = assetTypeBoxes[code];
      if (!box) return;
      any = true;
      if (box.checked) enabled.push(code); else anyOff = true;
    });
    if (!any || !anyOff) return null;
    return new Set(enabled);
  }

  /* Simple-map data check (Paul, Nov 17, 2026): which of the
     checklist files actually load. Roads fall back to the
     chapter's curated roads file, so they are available whenever
     either file loads. Warms the GeoJSON cache for the render. */
  async function simpleAvailable() {
    var out = { lakes: false, towns: false, roads: false };
    try { await fetchGeoJSON("simple-lakes.geojson"); out.lakes = true; }
    catch (e) {}
    try { await fetchGeoJSON("simple-towns.geojson"); out.towns = true; }
    catch (e) {}
    try { await fetchGeoJSON("simple-roads.geojson"); out.roads = true; }
    catch (e) {
      try { await fetchGeoJSON("roads.geojson"); out.roads = true; }
      catch (e2) {}
    }
    return out;
  }

  /* ------------------------------------------------------------- UI */
  function $(id) { return document.getElementById(id); }
  function setStatus(msg) {
    var el = $("export-status");
    if (el) el.textContent = msg;
  }
  function updateGoButton() {
    var go = $("export-go");
    if (!go) return;
    go.disabled = false;
    go.textContent = exportBounds ? "Download GeoPDF of the drawn area"
      : "Download GeoPDF of the current view";
  }
  function setDrawMode(on) {
    drawing = on;
    var btn = $("export-draw");
    if (btn) {
      btn.classList.toggle("active", on);
      btn.textContent = on ? "Drawing — drag a rectangle on the map…"
        : "Draw export area";
    }
    if (typeof map !== "undefined") {
      if (on) {
        map.dragging.disable();
        if (map.boxZoom) map.boxZoom.disable();
        map.getContainer().style.cursor = "crosshair";
      } else {
        map.dragging.enable();
        if (map.boxZoom) map.boxZoom.enable();
        map.getContainer().style.cursor = "";
      }
    }
  }
  function clearRect() {
    if (rectLayer && typeof map !== "undefined") map.removeLayer(rectLayer);
    rectLayer = null;
    exportBounds = null;
    updateGoButton();
    setStatus("Area cleared. Draw a rectangle, or export the current view.");
  }

  function wireMapEvents() {
    if (typeof map === "undefined") return;
    map.on("mousedown", function (e) {
      if (!drawing) return;
      startLatLng = e.latlng;
      if (rectLayer) map.removeLayer(rectLayer);
      rectLayer = L.rectangle(L.latLngBounds(startLatLng, startLatLng), {
        color: "#d7301f", weight: 2, fillColor: "#d7301f",
        fillOpacity: 0.08, interactive: false,
      }).addTo(map);
    });
    map.on("mousemove", function (e) {
      if (!drawing || !startLatLng || !rectLayer) return;
      rectLayer.setBounds(L.latLngBounds(startLatLng, e.latlng));
    });
    function finish(e) {
      if (!drawing || !startLatLng) return;
      var b = L.latLngBounds(startLatLng, e.latlng);
      startLatLng = null;
      if (b.getWest() === b.getEast() || b.getSouth() === b.getNorth()) {
        setStatus("That was a click, not a rectangle — drag a box.");
        return;
      }
      exportBounds = b;
      setDrawMode(false);
      updateGoButton();
      var w = (b.getEast() - b.getWest()).toFixed(3);
      var h = (b.getNorth() - b.getSouth()).toFixed(3);
      setStatus("Area set: " + w + "° × " + h + " lon/lat. " +
        "Tick the layers you want above, then Download GeoPDF.");
    }
    map.on("mouseup", finish);
    document.addEventListener("mouseup", function (e) {
      if (!drawing || !startLatLng) return;
      var pt = map.mouseEventToLatLng(e);
      finish({ latlng: pt });
    });
  }

  /* Shared download: render the given bounds as a GeoPDF and save it.
   * Used by the export page (doExport below) and by the in-viewer
   * print dialog (site/print-dialog.js, Paul Nov 17, 2026).
   * onStatus receives short progress lines; resolves to a one-line
   * summary, or rejects with the failure. */
  async function downloadGeoPdf(bounds, onStatus, opts) {
    var say = onStatus || function () {};
    if (typeof PDFLib === "undefined") {
      throw new Error("pdf-lib failed to load — check site/pdf-lib.min.js");
    }
    if (!window.ItmGeoPdf) {
      throw new Error("geopdf-writer.js failed to load");
    }
    if (!bounds) throw new Error("no map — the viewer did not load");
    var layerIds = onLayerIds();
    /* A Simple map replaces the panel layers with its own
       checklist, so it needs no layers ticked. */
    if (!layerIds.length && !(opts && opts.simple)) {
      throw new Error("no layers are ticked — tick at least one layer");
    }
    var title = "Itasca Moraine — Trail Map export";
    var subtitle = "Itasca Moraine Chapter, North Country Trail Association";
    say("Rendering…");
    var result = await renderExport(bounds, layerIds, title, subtitle, say, opts);
    say("Writing GeoPDF…");
    var blob = await new Promise(function (resolve, reject) {
      result.canvas.toBlob(function (b) {
        if (b) resolve(b);
        else reject(new Error("canvas to JPEG failed"));
      }, "image/jpeg", 0.85);
    });
    var jpegBytes = new Uint8Array(await blob.arrayBuffer());
    var pdfBytes = await window.ItmGeoPdf.writeGeoPdf({
      jpegBytes: jpegBytes,
      widthPx: result.canvas.width,
      heightPx: result.canvas.height,
      bboxLonLat: result.bbox,
      title: title,
      subject: subtitle,
      dpi: (opts && opts.dpi) || EXPORT_DPI,
    });
    var pdfBlob = new Blob([pdfBytes], { type: "application/pdf" });
    var stamp = new Date().toISOString().replace(/[-:T]/g, "")
      .slice(0, 12);
    var a = document.createElement("a");
    a.href = URL.createObjectURL(pdfBlob);
    a.download = "itasca-moraine-export-" + stamp + ".pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 60000);
    var mb = (pdfBlob.size / 1048576).toFixed(2);
    var paperLabel = "";
    if (opts && opts.simple) paperLabel += "Simple map · ";
    if (opts && opts.paper && PAPER_SIZES[opts.paper]) {
      paperLabel += PAPER_NAMES[opts.paper] + " " +
        (opts.orientation === "landscape" ? "landscape" : "portrait") +
        " · " + ((opts && opts.dpi) || EXPORT_DPI) + " dpi · ";
    }
    var skippedNote = "";
    if (result.simpleSkipped && result.simpleSkipped.length) {
      skippedNote = " (unavailable: " +
        result.simpleSkipped.join(", ") + ")";
    }
    return "Done — " + paperLabel + result.canvas.width + " × " +
      result.canvas.height + " px, zoom " + result.zoom + ", " +
      result.layers.length + " layers" + skippedNote + ", " + mb +
      " MB. Georeferenced (UTM 15N); opens in Avenza Maps and QGIS.";
  }

  async function doExport() {
    var go = $("export-go");
    if (go) go.disabled = true;
    try {
      var bounds = exportBounds ||
        (typeof map !== "undefined" ? map.getBounds() : null);
      setStatus(await downloadGeoPdf(bounds, function (msg) {
        setStatus(msg);
      }));
    } catch (err) {
      setStatus("Export failed: " + (err && err.message ? err.message : err));
      if (window.console) console.error(err);
    } finally {
      if (go) go.disabled = false;
    }
  }

  function init() {
    var drawBtn = $("export-draw");
    var goBtn = $("export-go");
    var clearBtn = $("export-clear");
    if (!drawBtn || !goBtn) return;
    drawBtn.addEventListener("click", function () {
      setDrawMode(!drawing);
      if (drawing) setStatus("Drag a rectangle on the map to choose the area.");
    });
    goBtn.addEventListener("click", doExport);
    if (clearBtn) clearBtn.addEventListener("click", clearRect);
    wireMapEvents();
    updateGoButton();
    setStatus("Tick the layers you want, draw a rectangle on the map, " +
      "then Download GeoPDF. The export always uses the simple street " +
      "basemap, whatever basemap the map is showing.");
  }

  /* Test hook: pure helpers + the canvas renderer, for node-side
     checks with a stub 2d context (no browser needed). */
  if (typeof window !== "undefined") {
    /* The print dialog (site/print-dialog.js) renders through here. */
    window.ItmExport = {
      downloadGeoPdf: downloadGeoPdf,
      onLayerIds: onLayerIds,
      renderExport: renderExport,
      simpleAvailable: simpleAvailable,
    };
    window.ItmExportTest = {
      lonToPx: lonToPx, latToPx: latToPx, tileLat: tileLat,
      chooseZoom: chooseZoom, drawLayer: drawLayer,
      legendRowsFor: legendRowsFor, drawLegend: drawLegend,
      drawTitleFooter: drawTitleFooter, RENDER_ORDER: RENDER_ORDER,
      LAYER_FILES: LAYER_FILES,
      paperPx: paperPx, fitBoundsToAspect: fitBoundsToAspect,
      pxToLon: pxToLon, pxToLat: pxToLat,
      PAPER_SIZES: PAPER_SIZES, PAPER_NAMES: PAPER_NAMES,
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

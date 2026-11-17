/* Print dialog — in-viewer printing (Paul, Nov 17, 2026).
 *
 * A printer icon sits next to the Copy link button in the panel.
 * Clicking it opens a dialog with one job:
 * make ONE map of either a box you draw or the current map window,
 * as a GeoPDF download. The map book stays on the export page; this
 * dialog deliberately has no layer list — it prints the layers
 * ticked in the left panel, whatever they are.
 *
 * Rendering is shared with the export page:
 * window.ItmExport.downloadGeoPdf(bounds, onStatus) in export.js.
 */
(function () {
  "use strict";

  var drawing = false;
  var startLatLng = null;
  var rectLayer = null;
  var drawnBounds = null;
  var mode = "window"; // "window" | "box"

  function $(id) { return document.getElementById(id); }
  function say(msg) {
    var el = $("print-status");
    if (el) el.textContent = msg;
  }

  function areaLabel(b) {
    var w = (b.getEast() - b.getWest()).toFixed(3);
    var h = (b.getNorth() - b.getSouth()).toFixed(3);
    return w + "° × " + h + " lon/lat";
  }

  function refresh() {
    var go = $("print-go");
    var redraw = $("print-redraw");
    if (!go) return;
    if (mode === "box" && !drawnBounds) {
      go.textContent = "Draw a box on the map";
      say("Pick an area: drag a rectangle on the map.");
    } else if (mode === "box") {
      go.textContent = "Download GeoPDF";
      say("Area set: " + areaLabel(drawnBounds) + ".");
    } else {
      go.textContent = "Download GeoPDF";
      say("");
    }
    if (redraw) redraw.hidden = !(mode === "box" && drawnBounds);
    go.disabled = false;
  }

  function openDialog() {
    var back = $("print-dialog-backdrop");
    if (!back) return;
    back.hidden = false;
    refresh();
  }
  function closeDialog() {
    var back = $("print-dialog-backdrop");
    if (!back) return;
    back.hidden = true;
    setDrawMode(false);
  }

  function setDrawMode(on) {
    drawing = on;
    if (typeof map === "undefined") return;
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
  function clearRect() {
    if (rectLayer && typeof map !== "undefined") map.removeLayer(rectLayer);
    rectLayer = null;
    drawnBounds = null;
  }

  function armDrawing() {
    closeDialog();
    clearRect();
    setDrawMode(true);
    say("Drag a rectangle on the map to choose the area.");
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
      setDrawMode(false);
      if (b.getWest() === b.getEast() || b.getSouth() === b.getNorth()) {
        say("That was a click, not a rectangle — drag a box.");
        return;
      }
      drawnBounds = b;
      mode = "box";
      var boxRadio = document.querySelector(
        'input[name="print-area"][value="box"]');
      if (boxRadio) boxRadio.checked = true;
      openDialog();
    }
    map.on("mouseup", finish);
    document.addEventListener("mouseup", function (e) {
      if (!drawing || !startLatLng) return;
      finish({ latlng: map.mouseEventToLatLng(e) });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (drawing) { setDrawMode(false); startLatLng = null; }
        closeDialog();
      }
    });
  }

  async function doPrint() {
    var go = $("print-go");
    if (mode === "box" && !drawnBounds) {
      armDrawing();
      return;
    }
    var bounds = mode === "box" ? drawnBounds :
      (typeof map !== "undefined" ? map.getBounds() : null);
    if (!bounds) { say("No map — the viewer did not load."); return; }
    if (!window.ItmExport || !window.ItmExport.downloadGeoPdf) {
      say("Print failed: the export engine did not load.");
      return;
    }
    if (go) go.disabled = true;
    try {
      say(await window.ItmExport.downloadGeoPdf(bounds, say));
    } catch (err) {
      say("Print failed: " + (err && err.message ? err.message : err));
      if (window.console) console.error(err);
    } finally {
      if (go) go.disabled = false;
    }
  }

  function init() {
    var btn = $("btn-print");
    var back = $("print-dialog-backdrop");
    if (!btn || !back) return;
    btn.addEventListener("click", openDialog);
    $("print-close").addEventListener("click", closeDialog);
    $("print-close-x").addEventListener("click", closeDialog);
    back.addEventListener("click", function (e) {
      if (e.target === back) closeDialog();
    });
    $("print-go").addEventListener("click", doPrint);
    $("print-redraw").addEventListener("click", armDrawing);
    var radios = document.querySelectorAll('input[name="print-area"]');
    radios.forEach(function (r) {
      r.addEventListener("change", function () {
        mode = r.value;
        refresh();
      });
    });
    /* Keep clicks on the button and the dialog from reaching the map
       underneath (otherwise a click on Print while drawing is armed
       would start a rectangle at the button). */
    if (window.L && L.DomEvent) {
      L.DomEvent.disableClickPropagation($("print-corner"));
      L.DomEvent.disableClickPropagation($("print-dialog-backdrop"));
    }
    wireMapEvents();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

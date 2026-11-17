/* GeoPDF writer for the Itasca Moraine trail map (Nov 16, 2026).
 *
 * Builds a georeferenced PDF from a rendered map image using pdf-lib
 * (vendored as pdf-lib.min.js). The georeferencing is the ISO 32000
 * /VP Measure dictionary — the same structure GDAL writes for the
 * script-generated books (scripts/export_geopdf.py), so any tool
 * that reads those GeoPDFs (QGIS, Avenza Maps, GDAL) reads these:
 *
 *   /VP [ << /Type /Viewport /BBox [0 0 W H] /Name (Map)
 *           /Measure << /Type /Measure /Subtype /GEO
 *             /Bounds [0 1 0 0 1 0 1 1]
 *             /LPTS   [0 1 0 0 1 0 1 1]      (normalised, y-up)
 *             /GPTS   [lat lon ...]          (lat first, TL BL BR TR)
 *             /GCS    << /Type /PROJCS /EPSG 32615 /WKT (...) >>
 *           >> >> ]
 *
 * The four GPTS corners are the exact corners of the rendered image
 * (a Web Mercator rendering, so the interior is linearised between
 * the corners — the same approximation every web GeoPDF export
 * makes; over a few-km sheet the residual is a few metres).
 * The /GCS is UTM zone 15N, matching the script books.
 *
 * Exposes window.ItmGeoPdf.writeGeoPdf(opts) -> Promise<Uint8Array>.
 * opts: { jpegBytes, widthPx, heightPx, bboxLonLat [w,s,e,n],
 *         title, author, subject, dpi }
 */
(function (global) {
  "use strict";

  /* UTM zone 15N WKT, ESRI style — byte-identical to the /GCS WKT
     GDAL writes into the script books (see the prototype PDF). */
  var UTM15N_WKT =
    "PROJCS[\"WGS_1984_UTM_Zone_15N\",GEOGCS[\"GCS_WGS_1984\"," +
    "DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137.0,298.257223563]]," +
    "PRIMEM[\"Greenwich\",0.0],UNIT[\"Degree\",0.0174532925199433]]," +
    "PROJECTION[\"Transverse_Mercator\"]," +
    "PARAMETER[\"False_Easting\",500000.0]," +
    "PARAMETER[\"False_Northing\",0.0]," +
    "PARAMETER[\"Central_Meridian\",-93.0]," +
    "PARAMETER[\"Scale_Factor\",0.9996]," +
    "PARAMETER[\"Latitude_Of_Origin\",0.0],UNIT[\"Meter\",1.0]]";

  function numArray(ctx, values) {
    var a = PDFLib.PDFArray.withContext(ctx);
    values.forEach(function (v) { a.push(PDFLib.PDFNumber.of(v)); });
    return a;
  }

  function name(s) { return PDFLib.PDFName.of(s); }

  async function writeGeoPdf(opts) {
    if (!global.PDFLib) {
      throw new Error("pdf-lib failed to load (PDFLib global missing)");
    }
    var dpi = opts.dpi || 150;
    var wPt = opts.widthPx * 72 / dpi;
    var hPt = opts.heightPx * 72 / dpi;
    var doc = await PDFLib.PDFDocument.create();
    var img = await doc.embedJpg(opts.jpegBytes);
    var page = doc.addPage([wPt, hPt]);
    page.drawImage(img, { x: 0, y: 0, width: wPt, height: hPt });

    /* Georeferencing: corners of the image in lon/lat. LPTS/Bounds
       are normalised page coordinates, y-up: TL, BL, BR, TR. GPTS
       are (lat, lon) pairs in the same corner order. */
    var w = opts.bboxLonLat[0], s = opts.bboxLonLat[1];
    var e = opts.bboxLonLat[2], n = opts.bboxLonLat[3];
    var ctx = doc.context;

    var gcs = PDFLib.PDFDict.withContext(ctx);
    gcs.set(name("Type"), name("PROJCS"));
    gcs.set(name("EPSG"), PDFLib.PDFNumber.of(32615));
    gcs.set(name("WKT"), PDFLib.PDFString.of(UTM15N_WKT));

    var measure = PDFLib.PDFDict.withContext(ctx);
    measure.set(name("Type"), name("Measure"));
    measure.set(name("Subtype"), name("GEO"));
    measure.set(name("Bounds"), numArray(ctx, [0, 1, 0, 0, 1, 0, 1, 1]));
    measure.set(name("LPTS"), numArray(ctx, [0, 1, 0, 0, 1, 0, 1, 1]));
    measure.set(name("GPTS"), numArray(ctx,
      [n, w, s, w, s, e, n, e]));
    measure.set(name("GCS"), gcs);

    var viewport = PDFLib.PDFDict.withContext(ctx);
    viewport.set(name("Type"), name("Viewport"));
    viewport.set(name("BBox"), numArray(ctx, [0, 0, wPt, hPt]));
    viewport.set(name("Name"), PDFLib.PDFString.of("Map"));
    viewport.set(name("Measure"), measure);

    var vp = PDFLib.PDFArray.withContext(ctx);
    vp.push(viewport);
    page.node.set(name("VP"), vp);

    doc.setTitle(opts.title || "Itasca Moraine — Trail Map");
    doc.setAuthor(opts.author ||
      "Itasca Moraine Chapter, North Country Trail Association");
    doc.setSubject((opts.subject || "") +
      (opts.subject ? "; " : "") +
      "Basemap © OpenStreetMap contributors");
    doc.setCreator("site/geopdf-writer.js (pdf-lib)");
    return doc.save();
  }

  global.ItmGeoPdf = { writeGeoPdf: writeGeoPdf };
})(window);

/* Finishing the Trail — build-out viewer v1.
 * Standalone page reusing the chapter map's Leaflet 1.9.4.
 * Data: site/buildout/data/*.geojson (built by build-data.py from the NCTA
 * nct_public line and the three drawn-route files in the NCT Drive folder).
 * Hard rules enforced here: $643,850 labeled not-submitted; no unverified
 * parcel-count claim; Mesabi shown as disputed, never complete; road type leads;
 * no posted speed limit is asserted anywhere — the MnDOT sources consulted
 * (Nov 13, 2026) publish no speed limit for any segment. AADT and shoulder
 * widths from MnDOT EMMA / TDMS and the 2024 Keypoints reports are shown on
 * road-walk popups where found; gaps are labeled as missing, never guessed.
 */
(function () {
  'use strict';

  var map = L.map('map', { zoomControl: true }).setView([47.1, -94.2], 7);
  /* Basemaps — ported from the main viewer (site/app.js) so the
     build-out viewer offers the same basemaps, in the same order,
     with the same labels and the same default (OpenTopoMap).
     Layer definitions and the BASES list are copied verbatim;
     only basemaps come over — no data layers (canopy height,
     parcels, assets, alerts). */
  var topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, maxNativeZoom: 17,
    attribution: "Map data: © OpenStreetMap contributors, SRTM | " +
      "map style: © OpenTopoMap (CC-BY-SA)",
  }).addTo(map);

  var osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
  });

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

  /* Added Nov 13, 2026 (Paul: year-by-year aerials, labelled by year
     and season): Esri Wayback year-end releases 2018–2025. Same
     rule as the 2014 entry — the release closest to (and on/before)
     Dec 31 of each year, from the Wayback config (198 releases,
     2014-02-20 → 2026-10-29, fetched 2026-11-13). Verified live
     over the chapter: z12 tiles at 5 points, HTTP 200 JPEG, each
     year byte-distinct. 2015–2017 are NOT added: at all 5 points
     they 301-redirect to release 31144 (2014-06-11) and return
     byte-identical tiles to the 2014 base. 2026 is NOT added: the
     current Aerial (Esri) base already serves the newest imagery.
     Tiles 301-redirect to the release that published that tile, so
     a year entry shows imagery "of that year or earlier". RELABELLED
     Nov 13, 2026 (Paul): the menu labels are the year the photo was
     actually taken (capture year, from Esri's per-release metadata
     SRC_DATE), not the release date — the release date is when Esri
     published the snapshot, and the photos inside it are older.
     Measured Nov 13 at 3 corridor points: 2025 release = 2024,
     2023 = 2019, 2022 = 2021, 2021 = 2017–19, 2019 = 2017,
     2014 = 1999. The 2018, 2020 and 2024 releases are UNMEASURED
     (metadata service timed out) — their labels still show the
     release year until they are measured. */
  var esriWayback2018 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/23448/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2018): Esri World Imagery " +
        "Wayback, release of 2018-12-14",
    });
  var esriWayback2019 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/4756/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2019): Esri World Imagery " +
        "Wayback, release of 2019-12-12",
    });
  var esriWayback2020 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/29260/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2020): Esri World Imagery " +
        "Wayback, release of 2020-12-16",
    });
  var esriWayback2021 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/26120/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2021): Esri World Imagery " +
        "Wayback, release of 2021-12-21",
    });
  var esriWayback2022 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/45134/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2022): Esri World Imagery " +
        "Wayback, release of 2022-12-14",
    });
  var esriWayback2023 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/56102/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2023): Esri World Imagery " +
        "Wayback, release of 2023-12-07",
    });
  var esriWayback2024 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/16453/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2024): Esri World Imagery " +
        "Wayback, release of 2024-12-12",
    });
  var esriWayback2025 = L.tileLayer(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/" +
      "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/13192/" +
      "{z}/{y}/{x}", {
      maxZoom: 18,
      attribution: "Aerial imagery (2025): Esri World Imagery " +
        "Wayback, release of 2025-12-18",
    });

  /* Added Nov 13, 2026 (Paul: year-by-year aerials): MnGeo
     Geospatial Image Service layers, same WMS endpoint and pattern
     as the hillshade (L.tileLayer.wms, MN_WMS). All verified live
     over the chapter with GetMap requests (2 km box around lat
     47.05, lon -95.0, 512x512 JPEG). nc13hm is the Spring Aerial
     Imagery Program leaf-off layer (spring 2013, 50 cm; covers the
     whole corridor, unlike nw14, which is blank over most of it).
     fall12 is the 2012 fall Central layer. The fsa* layers are the
     per-vintage NAIP mosaics (summer leaf-on); fsa2023/fsa2025 are
     in the menu as the 2023/2025 summer entries, beside the Dec
     Wayback entries for those years. usgs2006, fsa (2003) and doq (1991) are the older
     statewide layers. */
  var mnAerial2013Spring = L.tileLayer.wms(MN_WMS, {
    layers: "nc13hm", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2013, spring leaf-off): MnGeo / " +
      "Minnesota DNR (Spring Aerial Imagery Program)",
  });
  var mnAerial2012Fall = L.tileLayer.wms(MN_WMS, {
    layers: "fall12", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2012, fall): MnGeo",
  });
  var mnAerial2025 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2025", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2025 NAIP): USDA / MnGeo",
  });
  var mnAerial2023 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2023", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2023 NAIP): USDA / MnGeo",
  });
  var mnAerial2021 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2021", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2021 NAIP): USDA / MnGeo",
  });
  var mnAerial2019 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2019", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2019 NAIP): USDA / MnGeo",
  });
  var mnAerial2017 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2017", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2017 NAIP): USDA / MnGeo",
  });
  var mnAerial2015 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2015", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2015 NAIP): USDA / MnGeo",
  });
  var mnAerial2013 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2013", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2013 NAIP): USDA / MnGeo",
  });
  var mnAerial2010 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2010", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2010 NAIP): USDA / MnGeo",
  });
  var mnAerial2009 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2009", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2009 NAIP): USDA / MnGeo",
  });
  var mnAerial2008 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa2008", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2008 NAIP): USDA / MnGeo",
  });
  var mnAerial2006 = L.tileLayer.wms(MN_WMS, {
    layers: "usgs2006", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2006): USGS / MnGeo",
  });
  var mnAerial2003 = L.tileLayer.wms(MN_WMS, {
    layers: "fsa", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (2003): USDA FSA / MnGeo",
  });
  var mnAerial1991 = L.tileLayer.wms(MN_WMS, {
    layers: "doq", format: "image/jpeg", transparent: false,
    version: "1.1.1",
    attribution: "Aerial imagery (1991, black-and-white): USGS / MnGeo",
  });

  /* LiDAR Shaded is a COMPOSED base: OpenSnowMap's pistes are a
     transparent overlay tile set with no cartography of their own
     (OpenSnowMap's own base snow map stays unused -- its author
     discourages outside use), so this entry stacks the
     pistes over the MN LiDAR Hillshade, the site's relief
     register. The hillshade layer object is shared: Leaflet moves
     a layer between parents, never duplicates it. Verified over
     the chapter: OSM pistes (nordic ski trails) are drawn around
     Itasca State Park and the Leech Lake shore; much of the
     corridor has none mapped, and there the base reads as plain
     hillshade. */
  var snowPistes = L.tileLayer(
    "https://tiles.opensnowmap.org/pistes/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "Snow trails: OpenSnowMap, " +
        "© OpenStreetMap contributors",
    });
  var winterBase = L.layerGroup([mnHillshade, snowPistes]);

  var BASES = [
    { name: "Topo (OpenTopoMap)", code: "topo", label: "OpenTopoMap",
      layer: topo },
    /* Streets and Trails sit under Topo (Paul, Nov 13, 2026):
       they are the street-level working maps, so they read as
       sub-choices of Topo (indented, subChoice) rather than
       separate top-level bases. */
    { name: "Streets (OSM)", code: "streets", label: "OpenStreetMap",
      layer: osm, subChoice: true },
    { name: "Trails (CyclOSM)", code: "trails", label: "Trails",
      sub: "CyclOSM", layer: cyclosm, subChoice: true },
    /* LiDAR Shaded (Paul, Nov 13, 2026): Terrain and Winter were
       the same LiDAR hillshade — Winter was the hillshade plus the
       snow pistes — so they are one button now. It uses winterBase
       (hillshade + snow trails), so the snow trails are kept, and
       winter: true keeps the snowmobile emphasis. The generic
       Aerial (NAIP 2023/25) is gone the same day: the year menu
       below carries recent aerial photography (2025 Dec newest),
       so a separate undated Aerial was redundant. */
    { name: "LiDAR Shaded", code: "lidar", label: "Bare Earth MN LiDAR",
      layer: winterBase, winter: true },
    /* Added Nov 13, 2026 (Paul: year-by-year aerials, labelled by
       year and season): newest first, Wayback above NAIP within a
       year. All verified live over the corridor — see the tile-layer
       definitions above and the research note in SOURCES.md. The
       2014 entry sits in its chronological slot, not at the head.
       Leaf state is labelled only where it is leaf-off (2013
       spring); the rest carry no leaf label (Paul, Nov 13).
       RELABELLED Nov 13, 2026 (Paul): the Wayback entries are
       labelled by the year the photo was taken (capture year),
       not the release date — see the Wayback comment above. The
       2018, 2020 and 2024 releases are unmeasured, so those three
       labels still show the release year. */
    { name: "Aerial 2025 (Dec)", code: "aerial-2025", label: "Aerial 2024",
      sub: "Esri Wayback snapshot", layer: esriWayback2025 },
    { name: "Aerial 2025 (summer)", code: "aerial-2025-naip", label: "Aerial 2025 (summer)",
      sub: "NAIP", layer: mnAerial2025 },
    { name: "Aerial 2024 (Dec)", code: "aerial-2024", label: "Aerial 2024 (Dec)",
      sub: "Esri Wayback snapshot", layer: esriWayback2024 },
    { name: "Aerial 2023 (Dec)", code: "aerial-2023", label: "Aerial 2019",
      sub: "Esri Wayback snapshot", layer: esriWayback2023 },
    { name: "Aerial 2023 (summer)", code: "aerial-2023-naip", label: "Aerial 2023 (summer)",
      sub: "NAIP", layer: mnAerial2023 },
    { name: "Aerial 2022 (Dec)", code: "aerial-2022", label: "Aerial 2021",
      sub: "Esri Wayback snapshot", layer: esriWayback2022 },
    { name: "Aerial 2021 (Dec)", code: "aerial-2021", label: "Aerial 2017–19",
      sub: "Esri Wayback snapshot", layer: esriWayback2021 },
    { name: "Aerial 2021 (summer)", code: "aerial-2021-naip", label: "Aerial 2021 (summer)",
      sub: "NAIP", layer: mnAerial2021 },
    { name: "Aerial 2020 (Dec)", code: "aerial-2020", label: "Aerial 2020 (Dec)",
      sub: "Esri Wayback snapshot", layer: esriWayback2020 },
    { name: "Aerial 2019 (Dec)", code: "aerial-2019", label: "Aerial 2017",
      sub: "Esri Wayback snapshot", layer: esriWayback2019 },
    { name: "Aerial 2019 (summer)", code: "aerial-2019-naip", label: "Aerial 2019 (summer)",
      sub: "NAIP", layer: mnAerial2019 },
    { name: "Aerial 2018 (Dec)", code: "aerial-2018", label: "Aerial 2018 (Dec)",
      sub: "Esri Wayback snapshot", layer: esriWayback2018 },
    { name: "Aerial 2017 (summer)", code: "aerial-2017-naip", label: "Aerial 2017 (summer)",
      sub: "NAIP", layer: mnAerial2017 },
    { name: "Aerial 2015 (summer)", code: "aerial-2015-naip", label: "Aerial 2015 (summer)",
      sub: "NAIP", layer: mnAerial2015 },
    { name: "Aerial 2014 (Dec)", code: "aerial-2014", label: "Aerial 1999",
      sub: "Esri Wayback snapshot", layer: esriWayback2014 },
    { name: "Aerial 2013 (spring, leaf-off)", code: "aerial-2013-spring", label: "Aerial 2013 (spring, leaf-off)",
      sub: "MnGeo NW 50 cm · SAIP", layer: mnAerial2013Spring },
    { name: "Aerial 2013 (summer)", code: "aerial-2013-naip", label: "Aerial 2013 (summer)",
      sub: "NAIP", layer: mnAerial2013 },
    { name: "Aerial 2012 (fall)", code: "aerial-2012-fall", label: "Aerial 2012 (fall)",
      sub: "MnGeo Central", layer: mnAerial2012Fall },
    { name: "Aerial 2010 (summer)", code: "aerial-2010-naip", label: "Aerial 2010 (summer)",
      sub: "NAIP", layer: mnAerial2010 },
    { name: "Aerial 2009 (summer)", code: "aerial-2009-naip", label: "Aerial 2009 (summer)",
      sub: "NAIP", layer: mnAerial2009 },
    { name: "Aerial 2008 (summer)", code: "aerial-2008-naip", label: "Aerial 2008 (summer)",
      sub: "NAIP", layer: mnAerial2008 },
    { name: "Aerial 2006 (summer/fall)", code: "aerial-2006", label: "Aerial 2006 (summer/fall)",
      sub: "USGS 40-county · 1 m", layer: mnAerial2006 },
    { name: "Aerial 2003 (summer)", code: "aerial-2003", label: "Aerial 2003 (summer)",
      sub: "FSA", layer: mnAerial2003 },
    { name: "Aerial 1991 (black-and-white)", code: "aerial-1991", label: "Aerial 1991 (black-and-white)",
      sub: "USGS DOQ · 1 m", layer: mnAerial1991 },
    { name: "Aerial (Esri)", code: "esri-aerial", label: "ESRI World Imagery",
      layer: esriImagery },
    { name: "Aerial + Topo (NAIP 2023/25)", code: "aerial-topo", label: "Aerial + Topo",
      sub: "NAIP with topo labels", layer: usgsImageryTopo },
    { name: "USGS Topo 1:24k", code: "usgs", label: "USGS Topo",
      sub: "1:24k quadrangles", layer: usgsTopo },
    { name: "National Geographic (Esri)", code: "natgeo", label: "National Geographic",
      layer: esriNatGeo },
    /* Retired Nov 11, 2026 (design review §7): the two canopy
       bases are the Tree height overlay's source now, not
       choices. They stay defined above and are NOT listed here. */
  ];

  var currentBase = BASES[0];

  /* setBase, simplified for the build-out viewer: the main viewer's
     version also steps casing registers, the Winter snowmobile
     emphasis, the access-layer style and the share hash — none of
     those exist here (the build-out viewer has no casing registers,
     no snowmobile emphasis styling and no share-link hash), so this
     swaps the layer, marks the button and keeps the base-imagery
     body class. The `winter: true` flag on LiDAR Shaded is kept in
     BASES for fidelity; it has no effect here. */
  function setBase(name) {
    var def = null;
    BASES.forEach(function (b) { if (b.name === name) def = b; });
    if (!def || def === currentBase) return;
    map.removeLayer(currentBase.layer);
    map.addLayer(def.layer);
    currentBase = def;
    document.body.classList.toggle("base-imagery", /^Aerial/.test(name));
    markActiveBase(name);
  }

  var yearSelect = null;
  function isAerialYear(def) {
    return /^Aerial \d{4}/.test(def.name);
  }
  function markActiveBase(name) {
    document.querySelectorAll("#background-choices .bg-choice").forEach(function (row) {
      var on = row.getAttribute("data-base") === name;
      row.classList.toggle("on", on);
      row.setAttribute("aria-pressed", on ? "true" : "false");
    });
    /* Keep the year menu showing the current year aerial, or the
       placeholder when the current base is not a year aerial. */
    if (yearSelect) {
      yearSelect.value = isAerialYear({ name: name }) ? name : "";
    }
  }

  function wireSubToggleExpand(label, wrap, openLabel) {
    wrap.classList.add("sub-toggles", "collapsed");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tog-expand";
    btn.textContent = "▸";
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", "Show " + openLabel);
    btn.title = "Show " + openLabel;
    btn.addEventListener("click", function () {
      var collapsed = wrap.classList.toggle("collapsed");
      btn.textContent = collapsed ? "▸" : "▾";
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
      btn.setAttribute("aria-label",
        (collapsed ? "Show " : "Hide ") + openLabel);
      btn.title = (collapsed ? "Show " : "Hide ") + openLabel;
    });
    label.appendChild(btn);
  }

  (function buildBackground() {
    function rowFor(def) {
      /* A real button (aria-pressed + the "on" class), not a
         label + radio — the Basemap section is a set of
         actions, and the radio's checked state drifted from
         the "on" class markActiveBase maintains. A subChoice
         (Streets, Trails under Topo) is a full-size button
         like every other base (Paul, Nov 13, 2026); it sits
         right after Topo in the order, which is what marks it
         as belonging to Topo. */
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bg-choice" + (def.subChoice ? " bg-sub-choice" : "");
      btn.setAttribute("data-base", def.name);
      btn.setAttribute("aria-pressed",
        def === currentBase ? "true" : "false");
      if (def === currentBase) btn.classList.add("on");
      btn.textContent = def.label + " ";
      if (def.sub) {
        var sub = document.createElement("span");
        sub.className = "bg-sub";
        sub.textContent = "— " + def.sub;
        btn.appendChild(sub);
      }
      btn.addEventListener("click", function () {
        setBase(def.name);
      });
      return btn;
    }
    var main = document.getElementById("background-choices");
    if (!main) return;
    /* The year aerials live in one menu, newest first (BASES
       order), instead of a button per year. The menu sits at the
       BOTTOM of the Basemap section (Paul, Nov 13, 2026), after
       every base button. Every base is listed here now: the
       "More backgrounds" disclosure is gone, nothing hides
       behind it. */
    function yearMenu() {
      var wrap = document.createElement("div");
      wrap.className = "bg-year-wrap";
      var label = document.createElement("label");
      label.className = "bg-year-label";
      label.setAttribute("for", "bg-year-select");
      label.textContent = "Aerial photography by year";
      var note = document.createElement("div");
      note.className = "bg-year-note";
      note.textContent = "Wayback entries are labelled by the year the photo was taken; some span more than one year.";
      var sel = document.createElement("select");
      sel.id = "bg-year-select";
      sel.className = "bg-year-select";
      var ph = document.createElement("option");
      ph.value = "";
      ph.textContent = "Choose a year…";
      sel.appendChild(ph);
      BASES.forEach(function (def) {
        if (!isAerialYear(def)) return;
        var opt = document.createElement("option");
        opt.value = def.name;
        opt.textContent = def.label + " — " + def.sub;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", function () {
        if (sel.value) setBase(sel.value);
      });
      wrap.appendChild(label);
      wrap.appendChild(note);
      wrap.appendChild(sel);
      yearSelect = sel;
      return wrap;
    }
    BASES.forEach(function (def) {
      if (isAerialYear(def)) return; /* year aerials live in the
        menu, not as buttons */
      main.appendChild(rowFor(def));
    });
    main.appendChild(yearMenu()); /* the year menu sits at the
      bottom of the Basemap section (Paul, Nov 13, 2026) */
    /* Basemap is a pull-down (Paul, Nov 13, 2026): the buttons
       start hidden behind a disclosure on the Basemap heading;
       the button opens them. Same pattern as the layer
       sub-toggles. */
    var bgHead = document.getElementById("basemap-head");
    if (bgHead) wireSubToggleExpand(bgHead, main, "basemap choices");
  })();

  // Whole-Minnesota corridor: ND border to the Arrowhead, both gaps.
  map.fitBounds([[46.24, -96.73], [47.98, -91.37]], { padding: [20, 20] });

  var SURF = {
    foot:     { color: '#1a9850', label: 'Foot tread (off-road)', weight: 5 },
    paved:    { color: '#fdae61', label: 'Paved multi-use path', weight: 5 },
    road:     { color: '#d73027', label: 'On-road walk', weight: 5 },
    sidewalk: { color: '#999999', label: 'Sidewalk', weight: 4 },
    other:    { color: '#999999', label: 'Other / untyped', weight: 3, dashArray: '6 5' }
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function miles(p) {
    var m = p.len_miles;
    return (m == null ? '—' : (Math.round(m * 100) / 100) + ' mi');
  }

  function midpoint(f) {
    var cs = f.geometry.coordinates;
    if (f.geometry.type !== 'LineString' || !cs.length) return null;
    return cs[Math.floor(cs.length / 2)];
  }
  // inBox(f, [lon0, lon1, lat0, lat1]) — midpoint test for segment detectors.
  function inBox(f, b) {
    var m = midpoint(f);
    if (!m) return false;
    return m[0] >= b[0] && m[0] <= b[1] && m[1] >= b[2] && m[1] <= b[3];
  }
  // Fergus Falls town traverse (US-59 / MN-210 East crossings).
  var FERGUS_FALLS = [-96.11, -96.03, 46.25, 46.31];
  function isFergusFalls(f) { return inBox(f, FERGUS_FALLS); }
  // MN-169 in Ely (E. Sheridan St eastward).
  var ELY = [-91.84, -91.75, 47.90, 47.94];
  function isMn169Ely(f) { return inBox(f, ELY); }
  // Mesabi paved path paralleling Hwy 169 through Eagles Nest Twp.
  var EAGLES_NEST = [-92.16, -92.03, 47.82, 47.86];
  function isEaglesNestPaved(f) { return inBox(f, EAGLES_NEST); }
  // MN-135 Embarrass -> Tower road segments (NCTA line, lon ~-92.28, lat 47.60-47.81).
  // The Mesabi Trail's own wording: no usable shoulder; the NCTA line is stale here.
  function isMn135(f) {
    var cs = f.geometry.coordinates;
    if (f.geometry.type !== 'LineString') return false;
    return cs.some(function (c) { return c[0] > -92.31 && c[0] < -92.22 && c[1] > 47.59 && c[1] < 47.82; });
  }

  // MnDOT figures per road-walk segment (EMMA / TDMS AADT; 2024 Keypoints
  // shoulder widths; read Nov 13, 2026 — see docs/gap-mndot-live-data-report.md).
  // Detectors are geographic or by NCTA seg_name; where the reports do not
  // cover a stretch, the popup says so instead of guessing.
  function mndotNote(f) {
    var p = f.properties;
    if (isMn135(f)) {
      return '<p class="mndot"><strong>MnDOT figures (Nov 13, 2026) — MN-135, Embarrass to Tower:</strong> AADT 703–1,720 (2025): 793 north of CSAH 26 near Tower and 1,720 north of CSAH 100 (both popup-verified in EMMA; 703 is a map label). <strong>No paved shoulder</strong> Embarrass–Wahlsten–Tower — 4 ft stabilized unpaved, 6 ft entering Tower. This confirms the Mesabi Trail&rsquo;s &ldquo;no usable shoulder&rdquo; wording. Posted speed limit not published in the MnDOT sources consulted.</p>';
    }
    if (isMn169Ely(f)) {
      return '<p class="mndot"><strong>MnDOT figures (Nov 13, 2026) — MN-169 in Ely:</strong> AADT 5,542 (2025) on Sheridan St E; shoulders 8 ft paved + 1.5 ft unpaved at 19th Ave E, 10 ft paved leaving Ely east. Posted speed limit not published in the MnDOT sources consulted.</p>';
    }
    if (p.seg_name === 'CR-88') {
      return '<p class="mndot"><strong>MnDOT figures (Nov 13, 2026) — County State Aid Highway 88:</strong> 16.38 mi, Fergus Falls to the Wilkin County line. It is not one 39.5-mi road to the border. Shoulders (Keypoints 2024): Fergus Falls end 8 ft paved; mid-stretch no paved shoulder, 6 ft stabilized unpaved; near Rothsay no paved shoulder, 5 ft stabilized unpaved. Traffic near Rothsay about 190 vehicles/day (2022, map label). Posted speed limit not published in the MnDOT sources consulted.</p>';
    }
    if (p.seg_name === 'Red River Valley Provisional Route') {
      return '<p class="mndot"><strong>MnDOT figures (Nov 13, 2026) — Rothsay to the North Dakota border, 23.68 mi:</strong> not one road — a zigzag of Wilkin County roads, then US-75 from Kent to the Red River bridge. US-75 at Kent: AADT 1,355 (2025); in Kent 2 ft paved + 8 ft unpaved shoulder; north toward the border 2–3 ft paved + 5 ft unpaved. The Red River bridge itself is not in the Wilkin County report. No MnDOT shoulder data was found for the Wilkin county-road zigzag. Posted speed limit not published in the MnDOT sources consulted.</p>';
    }
    if (isFergusFalls(f)) {
      return '<p class="mndot"><strong>MnDOT figures (Nov 13, 2026) — through Fergus Falls:</strong> the route crosses US-59 and MN-210 East. US-59: AADT 6,008–7,118 in town (2025), 13,317 north of town; shoulder widths through town, including the Pelican River crossing, are <strong>not listed</strong> — an 11.1-mi gap in the Otter Tail report. MN-210 East: AADT 11,492 / 6,008 in town (2025); shoulders 10 ft paved entering town and through town, 12 ft paved + 2 ft unpaved at one stretch, 8 ft leaving town. Posted speed limit not published in the MnDOT sources consulted.</p>';
    }
    return null;
  }

  function gapPopup(f) {
    var p = f.properties;
    var s = SURF[p.surface] || SURF.other;
    var h = '<h3>' + esc(s.label) + '</h3>';
    h += '<p><strong>' + miles(p) + '</strong>';
    if (p.seg_name) h += ' &middot; ' + esc(p.seg_name);
    if (p.chapter) h += ' &middot; ' + esc(p.chapter) + ' chapter';
    h += '</p>';
    if (p.surface === 'road') {
      h += '<p>On-road walk.</p>';
      var mndot = mndotNote(f);
      if (mndot) h += mndot;
      else h += '<p>MnDOT traffic counts and shoulder widths are not available for this stretch. Posted speed limits were not found in the MnDOT sources consulted for any segment (Nov 13, 2026).</p>';
      if (isMn135(f)) {
        h += '<p class="warn"><strong>MN-135, Embarrass to Tower:</strong> the Mesabi Trail&rsquo;s own wording is &ldquo;no usable shoulder&rdquo; and &ldquo;NOT recommended to detour to the shoulder of Hwy 135.&rdquo; The as-built Mesabi Trail has replaced most of this road walk; the NCTA line shown here is stale. Final 0.5 mi stub disputed — see the Mesabi note in the panel.</p>';
      }
    }
    if (p.surface === 'paved') {
      h += '<p>Paved multi-use path (Mesabi Trail on the Arrowhead gap; Heart of the Lakes Trail on the western gap). This is the trail as it exists today — not off-road foot tread.</p>';
      if (isEaglesNestPaved(f)) {
        h += '<p class="mndot"><strong>Highway 169 alongside (MnDOT, Nov 13, 2026):</strong> rebuilt 2018, $16.4M, about 6 mi. Shoulders here are mostly 4 ft paved — 8 ft only leaving Tower, with one 10-ft stretch — not a uniform 8 ft. AADT 2,370 (2025) east of Soudan. Posted speed limit not published in the MnDOT sources consulted.</p>';
      }
    }
    if (p.surface === 'foot') {
      h += '<p>True off-road foot tread. On the Arrowhead gap this is 1.44 miles of 182.6; on the western gap 5.98 miles of 106.1.</p>';
    }
    return h;
  }

  function gapStyle(f) {
    var s = SURF[f.properties.surface] || SURF.other;
    return { color: s.color, weight: s.weight, opacity: 0.9, dashArray: s.dashArray || null };
  }

  var layers = {};
  var loaded = {};

  function fetchGeo(path) {
    return fetch(path).then(function (r) {
      if (!r.ok) throw new Error(path + ' HTTP ' + r.status);
      return r.json();
    });
  }

  function addGapLayer(id, path) {
    return fetchGeo(path).then(function (gj) {
      layers[id] = L.geoJSON(gj, { style: gapStyle, onEachFeature: function (f, l) {
        l.bindPopup(gapPopup(f));
      }});
      loaded[id] = true;
      if (document.getElementById('lyr-gaps').checked) layers[id].addTo(map);
    });
  }

  function addProposedArrowhead() {
    return fetchGeo('data/proposed-arrowhead.geojson').then(function (gj) {
      layers['prop-a'] = L.geoJSON(gj, {
        style: { color: '#2166ac', weight: 4, opacity: 0.95 },
        onEachFeature: function (f, l) {
          l.bindPopup('<h3>Proposed Arrowhead line</h3>' +
            '<p><strong>101.5 miles</strong> of new off-road footpath, Ely to north of Grand Rapids.</p>' +
            '<p>101 miles of footpath replaces about 165 miles of bike path and road (the Mesabi Trail dogleg).</p>' +
            '<p>Drawn line: &ldquo;North Country Trail &ndash; proposed 102 miles&rdquo; (KML, July 2025). Ground-truthed volunteer line; runs inside the congressionally approved 2004 corridor except where noted in the planning panel.</p>');
        }
      });
      loaded['prop-a'] = true;
      if (document.getElementById('lyr-prop-a').checked) layers['prop-a'].addTo(map);
    });
  }

  function addProposedWestern() {
    return fetchGeo('data/proposed-western.geojson').then(function (gj) {
      layers['prop-w'] = L.geoJSON(gj, {
        style: { color: '#2166ac', weight: 4, opacity: 0.95, dashArray: '10 4' },
        onEachFeature: function (f, l) {
          var name = f.properties.name || '';
          var mi = f.properties.length_mi;
          var extra = '';
          if (/west from FF/i.test(name)) extra = 'Fergus Falls to the North Dakota border at Fort Abercrombie — the Blue Corridor (river buffers) route.';
          else if (/north from FF/i.test(name)) extra = 'Fergus Falls to Frazee — the Green Corridor route, moving hikers off Becker County Highways 29 and 120 into existing public corridors.';
          else if (/alt 1/i.test(name)) extra = 'Short alternative stub (3.3 mi).';
          l.bindPopup('<h3>Proposed western line</h3>' +
            '<p><strong>' + esc(name) + ' — ' + mi + ' mi</strong></p>' +
            '<p>' + esc(extra) + '</p>' +
            '<p>Together the western lines total about 101 miles — the &ldquo;100-mile Western agricultural segment.&rdquo; Drawn by the Minnesota Waters and Prairie chapter (KML).</p>');
        }
      });
      loaded['prop-w'] = true;
      if (document.getElementById('lyr-prop-w').checked) layers['prop-w'].addTo(map);
    });
  }

  function addCorridor() {
    return fetchGeo('data/corridor-2004.geojson').then(function (gj) {
      layers['corridor'] = L.geoJSON(gj, {
        style: { color: '#2166ac', weight: 1.5, opacity: 0.6, fillColor: '#2166ac', fillOpacity: 0.08 },
        onEachFeature: function (f, l) {
          l.bindPopup('<h3>2004 approved corridor</h3>' +
            '<p>The congressionally approved planning corridor for the Arrowhead reroute (NPS Draft Route Assessment &amp; Environmental Assessment, 2004; authorized by Congress March 2019, Dingell Act, P.L. 116-9).</p>' +
            '<p>About a 200-foot-wide planning corridor. The Act authorizes the route; it appropriates no construction money.</p>');
        }
      });
      loaded['corridor'] = true;
      if (document.getElementById('lyr-corridor').checked) layers['corridor'].addTo(map);
    });
  }

  function addStreetView() {
    return fetchGeo('data/gap-streetview.geojson').then(function (gj) {
      layers['sv'] = L.geoJSON(gj, {
        pointToLayer: function (f, ll) {
          return L.marker(ll, { icon: L.divIcon({
            className: 'sv-marker', html: '&#9673;', iconSize: [20, 20], iconAnchor: [10, 10]
          })});
        },
        onEachFeature: function (f, l) {
          var p = f.properties;
          var h = '<h3>' + esc(p.name) + '</h3>' +
            '<p>' + esc(p.why) + '</p>';
          if (p.verified) {
            h += '<p><a href="' + esc(p.url) + '" target="_blank" rel="noopener">Open Street View</a> — panorama confirmed ' + esc(p.pano_date || '') + '.</p>';
            if (p.pano_note) h += '<p>' + esc(p.pano_note) + '</p>';
          } else {
            h += '<p class="warn"><strong>No Street View panorama on the road at this point.</strong></p>';
            if (p.pano_note) h += '<p>' + esc(p.pano_note) + '</p>';
            h += '<p><a href="' + esc(p.url) + '" target="_blank" rel="noopener">Open nearest panorama</a> (' + esc(p.pano_date || '') + ') — not a road view.</p>';
          }
          l.bindPopup(h);
        }
      });
      loaded['sv'] = true;
      if (document.getElementById('lyr-sv').checked) layers['sv'].addTo(map);
    });
  }

  // Ground conditions — planning mode only, off by default, lazy.
  // Land cover: NLCD 2021 as live WMS tiles from the MRLC GeoServer
  // (mrlc_display:NLCD_2021_Land_Cover_L48). The tile layer object is cheap
  // to create; no tiles are fetched until it is added to the map.
  var landcover = L.tileLayer.wms('https://www.mrlc.gov/geoserver/wms', {
    layers: 'mrlc_display:NLCD_2021_Land_Cover_L48',
    format: 'image/png',
    transparent: true,
    opacity: 0.55,
    attribution: 'NLCD 2021, USGS / MRLC'
  });

  var DRAIN = {
    'Very poorly drained': '#084594',
    'Poorly drained': '#2171b5',
    'Somewhat poorly drained': '#6baed6',
    'Moderately well drained': '#a6d96a',
    'Well drained': '#66bd63',
    'Somewhat excessively drained': '#fdae61',
    'Excessively drained': '#f46d43'
  };
  function soilMeaning(p) {
    var d = p.drainage;
    if (d === 'Very poorly drained' || d === 'Poorly drained')
      return 'Wet ground — expect boardwalk or puncheon; a dry footpath tread will not hold here.';
    if (d === 'Somewhat poorly drained')
      return 'Seasonally wet — tread needs drainage work; boardwalk likely in the low spots.';
    if (d === 'Moderately well drained' || d === 'Well drained')
      return 'Generally workable tread; check the low spots after rain.';
    if (d === 'Somewhat excessively drained' || d === 'Excessively drained')
      return 'Dry, sandy or gravelly — tread holds well but can erode on slopes.';
    return 'No drainage class recorded for this map unit.';
  }
  function soilPopup(p) {
    var h = '<h3>Soil — ' + esc(p.musym || p.mukey) + '</h3>';
    h += '<p>' + esc(p.muname || 'Map unit name not recorded') + '</p>';
    h += '<p><strong>Drainage:</strong> ' + esc(p.drainage || 'not recorded');
    if (p.hydric === 'Yes') h += ' &middot; <strong>hydric</strong> (wetland indicator)';
    else if (p.hydric === 'No') h += ' &middot; not hydric';
    h += '</p>';
    if (p.slope != null) h += '<p><strong>Slope:</strong> about ' + esc(p.slope) + '%</p>';
    if (p.flood && p.flood !== 'None') h += '<p><strong>Flooding:</strong> ' + esc(p.flood) + '</p>';
    h += '<p>' + esc(soilMeaning(p)) + '</p>';
    if (p.hydric === 'Yes')
      h += '<p class="warn">Hydric soil is a wetland indicator — expect permitting questions where the line crosses it.</p>';
    h += '<p class="drawn-note">USDA NRCS SSURGO, via Soil Data Access, retrieved Nov 13, 2026. Map unit ' + esc(p.mukey) + '.</p>';
    return h;
  }
  function soilStyle(f) {
    return {
      color: '#555555', weight: 0.5, opacity: 0.7,
      fillColor: DRAIN[f.properties.drainage] || '#cccccc',
      fillOpacity: 0.45
    };
  }
  var soilsLoading = false;
  function addSoils() {
    if (loaded['soils'] || soilsLoading) return;
    soilsLoading = true;
    fetchGeo('data/soils-corridor.geojson').then(function (gj) {
      layers['soils'] = L.geoJSON(gj, {
        style: soilStyle,
        onEachFeature: function (f, l) { l.bindPopup(soilPopup(f.properties)); }
      });
      loaded['soils'] = true;
      // Soils sit under the gap and proposed lines so their popups win.
      layers['soils'].bringToBack();
      if (layers['gap-a']) layers['gap-a'].bringToFront();
      if (layers['gap-w']) layers['gap-w'].bringToFront();
      if (layers['prop-a']) layers['prop-a'].bringToFront();
      if (layers['prop-w']) layers['prop-w'].bringToFront();
      if (document.getElementById('lyr-soils').checked) layers['soils'].addTo(map);
    }).catch(function (err) {
      soilsLoading = false;
      if (window.console && console.error) console.error('soils load failed:', err);
    });
  }

  // Motorized competition — planning mode only, off by default, lazy.
  // Geometries from the Minnesota DNR OHV Trails (2026 season) and
  // Snowmobile Trails services, clipped to 2 mi around the proposed
  // Arrowhead line and the 2004 corridor (build-motorized.py).
  var ATV_COLOR = '#762a83';   // purple — distinct from foot tread green
  var SNOW_COLOR = '#67a9cf';  // icy blue
  var motorLoading = {};
  function atvPopup(p) {
    var h = '<h3>ATV &mdash; ' + esc(p.name) + '</h3>';
    if (p.segment) h += '<p>' + esc(p.segment) + '</p>';
    if (p.classes) h += '<p><strong>Vehicles:</strong> ' + esc(p.classes) + '</p>';
    if (p.surface) h += '<p><strong>Surface:</strong> ' + esc(p.surface) + '</p>';
    if (p.funding) h += '<p><strong>Funding:</strong> ' + esc(p.funding) + '</p>';
    if (p.pub_miles != null) h += '<p><strong>This segment:</strong> ' + esc(p.pub_miles) + ' mi (DNR service)</p>';
    if (/^prospectors$/i.test(p.name))
      h += '<p class="warn"><strong>Mileage disputed:</strong> DNR lists 167 mi; the club says 216+ mi; a consultant says 250 mi. The panel shows DNR&rsquo;s figure and notes the dispute.</p>';
    if (p.website) h += '<p><a href="' + esc(p.website) + '" target="_blank" rel="noopener">DNR trail page</a></p>';
    h += '<p class="drawn-note">Minnesota DNR OHV Trails, 2026 season, via the MnGeo FeatureServer. Lines within 2 mi of the proposed Arrowhead line / 2004 corridor.</p>';
    return h;
  }
  // Brainerd-to-Canada layer popup: published (DNR A-Z / county GIA) miles
  // and manager from the research inventory, not GIS-measured miles.
  function atvBcPopup(p) {
    var h = '<h3>ATV &mdash; ' + esc(p.name) + '</h3>';
    if (p.pub_miles != null) h += '<p><strong>' + esc(p.pub_miles) + ' mi</strong> designated (DNR A-Z / county GIA, Nov 13, 2026)</p>';
    if (p.manager) h += '<p><strong>Manager:</strong> ' + esc(p.manager) + '</p>';
    if (p.county) h += '<p><strong>County:</strong> ' + esc(p.county) + '</p>';
    if (p.segment) h += '<p>' + esc(p.segment) + '</p>';
    if (p.classes) h += '<p><strong>Vehicles:</strong> ' + esc(p.classes) + '</p>';
    if (p.surface) h += '<p><strong>Surface:</strong> ' + esc(p.surface) + '</p>';
    if (p.funding) h += '<p><strong>Funding:</strong> ' + esc(p.funding) + '</p>';
    if (/OHM only/i.test(p.name))
      h += '<p class="warn"><strong>OHM only, not ATV</strong> — counted in the 1,630.5-mi corridor total per the DNR A-Z convention, excluded from the 1,599.5-mi ATV-only figure.</p>';
    if (p.service_name) h += '<p class="drawn-note">DNR service name: ' + esc(p.service_name) + '.</p>';
    if (p.source) h += '<p><a href="' + esc(p.source) + '" target="_blank" rel="noopener">Source</a></p>';
    h += '<p class="drawn-note">Brainerd-to-Canada layer: the designated system drawn whole, from the Minnesota DNR OHV Trails service (2026 season). Published miles are the DNR A-Z / county figures — the service geometry measures differently for some systems; see the panel.</p>';
    return h;
  }
  var SNOW_SHARED = {
    'Taconite State Trail': 'ATV is allowed on 11 mi (Ely&ndash;Purvis, May 15&ndash;Oct 31) and the 18-mi Big Aspen Connection &mdash; this groomed spine is shared-use in places.',
    'C.J. Ramstad/North Shore State Trail': 'The only ATV miles on this trail are a 7-mi segment in Lake County; HF 274 (2025) proposes ATV use on the Cook and Lake County portions.'
  };
  function snowPopup(p) {
    var h = '<h3>Snowmobile &mdash; ' + esc(p.name) + '</h3>';
    if (p.segment) h += '<p>' + esc(p.segment) + '</p>';
    if (p.maintained_by) h += '<p><strong>Maintained by:</strong> ' + esc(p.maintained_by) + '</p>';
    if (p.owner) h += '<p><strong>Owner:</strong> ' + esc(p.owner) + '</p>';
    if (p.trail_num != null) h += '<p><strong>Trail no.:</strong> ' + esc(p.trail_num) + '</p>';
    if (p.stud_restr) h += '<p><strong>Stud restriction:</strong> ' + esc(p.stud_restr) + '</p>';
    if (p.pub_miles != null) h += '<p><strong>This segment:</strong> ' + esc(p.pub_miles) + ' mi (DNR service)</p>';
    if (SNOW_SHARED[p.name]) h += '<p>' + SNOW_SHARED[p.name] + '</p>';
    h += '<p class="drawn-note">Minnesota DNR Snowmobile Trails, via the MnGeo FeatureServer. Groomed corridors run 20&ndash;26 ft wide (32&ndash;36 ft at crossings), groomers up to 17,000 lb.</p>';
    return h;
  }
  function addMotorized(id, path, color, popupFn) {
    if (loaded[id] || motorLoading[id]) return;
    motorLoading[id] = true;
    fetchGeo(path).then(function (gj) {
      layers[id] = L.geoJSON(gj, {
        style: { color: color, weight: 3, opacity: 0.85 },
        onEachFeature: function (f, l) { l.bindPopup(popupFn(f.properties)); }
      });
      loaded[id] = true;
      // Motorized sits under the gap and proposed lines so their popups win.
      layers[id].bringToBack();
      if (layers['gap-a']) layers['gap-a'].bringToFront();
      if (layers['gap-w']) layers['gap-w'].bringToFront();
      if (layers['prop-a']) layers['prop-a'].bringToFront();
      if (layers['prop-w']) layers['prop-w'].bringToFront();
      var box = document.getElementById('lyr-' + id);
      if (box && box.checked) {
        layers[id].addTo(map);
        // First load of the Brainerd-to-Canada layer: zoom to the corridor
        // (Brainerd to the border), which runs past the default two-gap view.
        if (id === 'atv-bc') map.fitBounds(layers[id].getBounds().pad(0.05));
      }
    }).catch(function (err) {
      motorLoading[id] = false;
      if (window.console && console.error) console.error(id + ' load failed:', err);
    });
  }

  function applyGroundLayers() {
    // Ground layers are planning-only: in briefing mode they leave the map
    // (checkboxes keep their state for the return to planning).
    var planning = !document.getElementById('planning-panel').hidden;
    if (document.getElementById('lyr-landcover').checked && planning) landcover.addTo(map);
    else map.removeLayer(landcover);
    if (loaded['soils']) {
      if (document.getElementById('lyr-soils').checked && planning) layers['soils'].addTo(map);
      else map.removeLayer(layers['soils']);
    } else if (document.getElementById('lyr-soils').checked && planning) {
      addSoils();
    }
    applyMotorLayer('atv', 'lyr-atv', 'data/motorized-atv.geojson', ATV_COLOR, atvPopup, planning);
    applyMotorLayer('snow', 'lyr-snow', 'data/motorized-snow.geojson', SNOW_COLOR, snowPopup, planning);
    applyMotorLayer('atv-bc', 'lyr-atv-bc', 'data/motorized-atv-bc.geojson', ATV_COLOR, atvBcPopup, planning);
  }
  function applyMotorLayer(id, checkboxId, path, color, popupFn, planning) {
    var on = document.getElementById(checkboxId).checked && planning;
    if (loaded[id]) {
      if (on) layers[id].addTo(map); else map.removeLayer(layers[id]);
    } else if (on) {
      addMotorized(id, path, color, popupFn);
    }
  }

  function toggleLayer(id, on) {
    var l = layers[id];
    if (!l) return;
    if (on) l.addTo(map); else map.removeLayer(l);
  }

  document.getElementById('lyr-gaps').addEventListener('change', function (e) {
    toggleLayer('gap-a', e.target.checked);
    toggleLayer('gap-w', e.target.checked);
  });
  document.getElementById('lyr-prop-a').addEventListener('change', function (e) { toggleLayer('prop-a', e.target.checked); });
  document.getElementById('lyr-prop-w').addEventListener('change', function (e) { toggleLayer('prop-w', e.target.checked); });
  document.getElementById('lyr-corridor').addEventListener('change', function (e) { toggleLayer('corridor', e.target.checked); });
  document.getElementById('lyr-sv').addEventListener('change', function (e) { toggleLayer('sv', e.target.checked); });
  document.getElementById('lyr-landcover').addEventListener('change', applyGroundLayers);
  document.getElementById('lyr-soils').addEventListener('change', applyGroundLayers);
  document.getElementById('lyr-atv').addEventListener('change', applyGroundLayers);
  document.getElementById('lyr-snow').addEventListener('change', applyGroundLayers);
  document.getElementById('lyr-atv-bc').addEventListener('change', applyGroundLayers);

  // Mode toggle: briefing (default) vs planning. Same map; planning adds the
  // readiness / funding / risks panel.
  var btnB = document.getElementById('mode-briefing');
  var btnP = document.getElementById('mode-planning');
  var note = document.getElementById('mode-note');
  var planningPanel = document.getElementById('planning-panel');
  var motorizedToggles = document.getElementById('motorized-toggles');
  function setMode(mode) {
    var planning = mode === 'planning';
    btnB.classList.toggle('active', !planning);
    btnP.classList.toggle('active', planning);
    btnB.setAttribute('aria-selected', String(!planning));
    btnP.setAttribute('aria-selected', String(planning));
    planningPanel.hidden = !planning;
    motorizedToggles.hidden = !planning;
    note.textContent = planning
      ? 'For chapter discussions: readiness, funding status, and the risks the chapters named.'
      : 'For the congressional delegation: the case on one screen.';
    applyGroundLayers();
    try { window.location.hash = mode === 'planning' ? '#planning' : '#briefing'; } catch (e) { /* no-op */ }
  }
  btnB.addEventListener('click', function () { setMode('briefing'); });
  btnP.addEventListener('click', function () { setMode('planning'); });
  if (window.location.hash === '#planning') setMode('planning');

  Promise.all([
    addGapLayer('gap-a', 'data/gap-arrowhead.geojson'),
    addGapLayer('gap-w', 'data/gap-western.geojson'),
    addProposedArrowhead(),
    addProposedWestern(),
    addCorridor(),
    addStreetView()
  ]).then(function () {
    // Draw order: corridor wash at the back, gap lines above it so their
    // popups win the click, proposed lines on top.
    if (layers['gap-a']) layers['gap-a'].bringToFront();
    if (layers['gap-w']) layers['gap-w'].bringToFront();
    if (layers['prop-a']) layers['prop-a'].bringToFront();
    if (layers['prop-w']) layers['prop-w'].bringToFront();
    map.fitBounds([[46.24, -96.73], [47.98, -91.37]], { padding: [20, 20] });
  }).catch(function (err) {
    // Keep the page usable if one file fails; log for the builder.
    if (window.console && console.error) console.error('buildout data load failed:', err);
  });
})();

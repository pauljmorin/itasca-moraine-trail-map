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
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

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
      var box = document.getElementById(id === 'atv' ? 'lyr-atv' : 'lyr-snow');
      if (box && box.checked) layers[id].addTo(map);
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

  // Mode toggle: briefing (default) vs planning. Same map; planning adds the
  // readiness / funding / risks panel.
  var btnB = document.getElementById('mode-briefing');
  var btnP = document.getElementById('mode-planning');
  var note = document.getElementById('mode-note');
  var planningPanel = document.getElementById('planning-panel');
  function setMode(mode) {
    var planning = mode === 'planning';
    btnB.classList.toggle('active', !planning);
    btnP.classList.toggle('active', planning);
    btnB.setAttribute('aria-selected', String(!planning));
    btnP.setAttribute('aria-selected', String(planning));
    planningPanel.hidden = !planning;
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

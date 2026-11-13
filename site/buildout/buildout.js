/* Finishing the Trail — build-out viewer v1.
 * Standalone page reusing the chapter map's Leaflet 1.9.4.
 * Data: site/buildout/data/*.geojson (built by build-data.py from the NCTA
 * nct_public line and the three drawn-route files in the NCT Drive folder).
 * Hard rules enforced here: $643,850 labeled not-submitted; no unverified
 * parcel-count claim; Mesabi shown as disputed, never complete; road type leads;
 * speeds only as the 55 mph statutory default, labeled as such.
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

  // Town traverses: the 55 mph rural default does not apply inside town.
  // Each entry is [lon0, lon1, lat0, lat1].
  var TOWNS = [
    [-91.87, -91.83, 47.89, 47.94],   // Ely
    [-96.11, -96.03, 46.25, 46.31],   // Fergus Falls
    [-93.60, -93.52, 47.21, 47.25]    // Grand Rapids / Coleraine
  ];
  function midpoint(f) {
    var cs = f.geometry.coordinates;
    if (f.geometry.type !== 'LineString' || !cs.length) return null;
    return cs[Math.floor(cs.length / 2)];
  }
  function isTown(f) {
    var m = midpoint(f);
    if (!m) return false;
    return TOWNS.some(function (t) { return m[0] >= t[0] && m[0] <= t[1] && m[1] >= t[2] && m[1] <= t[3]; });
  }
  // MN-135 Embarrass -> Tower road segments (NCTA line, lon ~-92.28, lat 47.60-47.81).
  // The Mesabi Trail's own wording: no usable shoulder; the NCTA line is stale here.
  function isMn135(f) {
    var cs = f.geometry.coordinates;
    if (f.geometry.type !== 'LineString') return false;
    return cs.some(function (c) { return c[0] > -92.31 && c[0] < -92.22 && c[1] > 47.59 && c[1] < 47.82; });
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
      h += '<p>On-road walk.';
      if (!isTown(f)) h += ' Rural two-lane roads here carry the 55 mph statutory default (Minn. Stat. &sect; 169.14) — a default, not a posted limit.';
      h += ' Posted speeds, shoulder widths and traffic counts are not yet verified for this segment.</p>';
      if (isMn135(f)) {
        h += '<p class="warn"><strong>MN-135, Embarrass to Tower:</strong> the Mesabi Trail&rsquo;s own wording is &ldquo;no usable shoulder&rdquo; and &ldquo;NOT recommended to detour to the shoulder of Hwy 135.&rdquo; The as-built Mesabi Trail has replaced most of this road walk; the NCTA line shown here is stale. Final 0.5 mi stub disputed — see the Mesabi note in the panel.</p>';
      }
    }
    if (p.surface === 'paved') {
      h += '<p>Paved multi-use path (Mesabi Trail on the Arrowhead gap; Heart of the Lakes Trail on the western gap). This is the trail as it exists today — not off-road foot tread.</p>';
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
          l.bindPopup('<h3>' + esc(p.name) + '</h3>' +
            '<p>' + esc(p.why) + '</p>' +
            '<p><a href="' + esc(p.url) + '" target="_blank" rel="noopener">Open Street View</a></p>' +
            '<p class="warn"><strong>Panorama not yet confirmed</strong> — this link opens the nearest panorama to the viewpoint; existence has not been live-verified.</p>');
        }
      });
      loaded['sv'] = true;
      if (document.getElementById('lyr-sv').checked) layers['sv'].addTo(map);
    });
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

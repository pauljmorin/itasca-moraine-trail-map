#!/usr/bin/env python3
"""Build the 2022 (second-generation) LiDAR trio bases for the site.

Paul's plan (Nov 11, 2026): run the CURRENT (2022) trio first and
measure its real cost; the gen-1 / change-strip extension is NOT
part of this script. Bare earth already ships as the MnGeo WMS
hillshade; this script builds the two missing surfaces over a
~100 m corridor either side of the depicted trail lines:

  1. "MN LiDAR Canopy"        -- hillshade of the first-return
                                 surface (DSM), grey, same visual
                                 language as the bare-earth shade.
  2. "Canopy height (LiDAR)"  -- CHM = DSM - DTM as a colour ramp
                                 (pale ground at ~0 m to deep green
                                 at 25 m+), so clearcuts/fields read
                                 bare and mature canopy reads dark.

DATA SOURCES (see SOURCES.md for the full provenance + the fork):
  DTM: MnGeo seamless second-generation 0.5 m DEM VRT
       (ground model; corridor flown spring 2022, leaf-off).
  DSM: NO published statewide gen-2 DSM derivative exists, and the
       USGS block first-return DSM tiles + the per-tile LAZ files
       are staged only on rockyweb.usgs.gov, which sits behind a
       bot wall (UA-gated, ~50 KB/s single stream, 429s on any
       concurrency) -- measured 2026-11-11, not viable for ~250
       tiles. The SAME USGS point clouds are mirrored as Entwine
       EPT datasets on the public S3 bucket `usgs-lidar-public`
       (Registry of Open Data), which serves freely. This script
       reads the EPT octrees directly: MN_BeckerCo_1_2021 +
       MN_UpperMissRiver_{2,4,5,6}_B22 (units 1 and 3 do not
       intersect the corridor). First returns only, noise classes
       7/18 excluded, max height per 1 m cell.

TOOLING: needs numpy, rasterio, laspy[lazrs], shapely, pyproj,
pillow. The 2026-11-11 build installed pinned wheels into
working/lidar-trio/pylibs (pip --target); this script adds that
directory to sys.path when present. On a fresh machine:
  pip install "numpy==2.2.6" "rasterio==1.4.3" "laspy[lazrs]" \
      "shapely==2.0.7" pyproj pillow
(apt gdal-bin was attempted first on the build VM; its mirror
stalled indefinitely, so pip wheels were used -- friction logged
in the build report.)

STAGES (each timed; timings accumulate in
working/lidar-trio/stage-timings.json):
  index   -- traverse EPT hierarchies, list nodes intersecting
             the corridor buffer -> working/lidar-trio/node-index.json
  dsm     -- stream EPT chunks, bin first-return max at 1 m
             (EPSG:6344) into per-chunk GeoTIFFs
  dtm     -- read the seamless DEM VRT per chunk at 1 m; derive
             CHM + shade-surface chunks
  tiles   -- render PNG tiles z9..16 into
             site/tiles/canopy-shade/ and site/tiles/canopy-height/
  check   -- sample-check: find a mature stand + a clearing in the
             CHM near the trail, report spot heights, render
             sample sheets to working/lidar-trio/samples/
  all     -- index, dsm, dtm, tiles, check

Everything under working/lidar-trio/ is scratch (gitignored);
only the tiles under site/tiles/ and the site wiring ship.
"""

import json
import math
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "working", "lidar-trio")
PYLIBS = os.path.join(WORK, "pylibs")
if os.path.isdir(PYLIBS) and PYLIBS not in sys.path:
    sys.path.insert(0, PYLIBS)

import numpy as np  # noqa: E402

TRAIL_FILE = os.path.join(
    ROOT, "data", "segments", "official-line-chapter-extent.geojson")
DEM_VRT = ("https://g46prsaddst01.blob.core.windows.net/mntopo/"
           "dem_100k/2nd_Generation_Seamless_Lidar_DEM.vrt")
EPT_BASE = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public"
DATASETS = [
    "MN_BeckerCo_1_2021",
    "MN_UpperMissRiver_2_B22",
    "MN_UpperMissRiver_4_B22",
    "MN_UpperMissRiver_5_B22",
    "MN_UpperMissRiver_6_B22",
]
CRS_LIDAR = "EPSG:6344"        # NAD83(2011) UTM 15N -- lidar native
CELL = 1.0                     # DSM/CHM grid, metres
CHUNK = 5000                   # chunk size, metres (5000x5000 cells)
GRID_X0, GRID_Y0 = 300000, 5200000   # grid origin, EPSG:6344
BAND_M = 150.0                 # rendered corridor half-width (m):
                               # Paul's ~100 m + ragged tile margin
SELECT_M = 340.0               # point-selection half-width (m,
                               # ground) -- superset of BAND_M
NOISE_CLASSES = (7, 18)        # LAS low/high noise
TIMINGS = os.path.join(WORK, "stage-timings.json")
UA = {"User-Agent": "itasca-trail-map lidar build (public data)"}


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def timed(stage, fn):
    t0 = time.time()
    out = fn()
    dt = time.time() - t0
    rec = {}
    if os.path.exists(TIMINGS):
        rec = json.load(open(TIMINGS))
    rec[stage] = round(dt, 1)
    json.dump(rec, open(TIMINGS, "w"), indent=1)
    log("stage %s done in %.1fs" % (stage, dt))
    return out


import threading  # noqa: E402

_tls = threading.local()


def _session():
    """Per-thread requests.Session (connection pooling). The build
    VM's egress proxy makes a fresh TLS connection cost ~2 s, so
    pooling is the difference between minutes and hours on the
    many-small-files stages. Falls back to urllib if requests is
    unavailable."""
    s = getattr(_tls, "s", None)
    if s is None:
        try:
            import requests
            s = requests.Session()
            s.headers.update(UA)
        except Exception:  # noqa: BLE001
            s = False
        _tls.s = s
    return s


def fetch(url, dest, retries=3):
    """Download url to dest (skip if a non-trivial file exists)."""
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return os.path.getsize(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last = None
    for i in range(retries):
        try:
            s = _session()
            if s:
                with s.get(url, timeout=(15, 60), stream=True) as r:
                    r.raise_for_status()
                    with open(dest + ".part", "wb") as f:
                        for buf in r.iter_content(1 << 20):
                            f.write(buf)
            else:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r, \
                        open(dest + ".part", "wb") as f:
                    while True:
                        buf = r.read(1 << 20)
                        if not buf:
                            break
                        f.write(buf)
            os.rename(dest + ".part", dest)
            return os.path.getsize(dest)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("fetch failed %s: %s" % (url, last))


# ------------------------------------------------------------------
# Trail geometry helpers
# ------------------------------------------------------------------

def trail_lines(crs):
    from shapely.geometry import shape
    from shapely.ops import transform as shp_transform
    from pyproj import Transformer
    d = json.load(open(TRAIL_FILE))
    lines = [shape(f["geometry"]) for f in d["features"]
             if f["geometry"]["type"] in ("LineString", "MultiLineString")]
    if crs == 4326:
        return lines
    t = Transformer.from_crs(4326, crs, always_xy=True)
    return [shp_transform(t.transform, ln) for ln in lines]


def band_chunks():
    """Chunk slots (cx, cy) whose square intersects the SELECT band."""
    from shapely.geometry import box
    lines = trail_lines(6344)
    from shapely.ops import unary_union
    band = unary_union(lines).buffer(SELECT_M + CHUNK)
    slots = []
    xs = [ln.bounds for ln in lines]
    minx = min(b[0] for b in xs) - SELECT_M
    maxx = max(b[2] for b in xs) + SELECT_M
    miny = min(b[1] for b in xs) - SELECT_M
    maxy = max(b[3] for b in xs) + SELECT_M
    cx0 = int((minx - GRID_X0) // CHUNK)
    cx1 = int((maxx - GRID_X0) // CHUNK)
    cy0 = int((miny - GRID_Y0) // CHUNK)
    cy1 = int((maxy - GRID_Y0) // CHUNK)
    for cx in range(cx0, cx1 + 1):
        for cy in range(cy0, cy1 + 1):
            sq = box(GRID_X0 + cx * CHUNK, GRID_Y0 + cy * CHUNK,
                     GRID_X0 + (cx + 1) * CHUNK,
                     GRID_Y0 + (cy + 1) * CHUNK)
            if sq.intersects(band):
                slots.append((cx, cy))
    return slots


def chunk_bounds(cx, cy):
    return (GRID_X0 + cx * CHUNK, GRID_Y0 + cy * CHUNK,
            GRID_X0 + (cx + 1) * CHUNK, GRID_Y0 + (cy + 1) * CHUNK)


# ------------------------------------------------------------------
# Stage: index -- EPT hierarchy traversal
# ------------------------------------------------------------------

def ept_node_box(meta, key):
    """XY box of an EPT node. Verified empirically 2026-11-11:
    anchor = ept.json bounds min; cube side = max(bounds span x/y);
    node size = side / 2^depth. (Node 3-4-2-3 of MN_BeckerCo_1_2021
    predicted y 5910019..5924422 vs actual point extent
    5910047..5924412.)"""
    d, x, y, _z = (int(v) for v in key.split("-"))
    b = meta["bounds"]
    side = max(b[3] - b[0], b[4] - b[1])
    size = side / (2 ** d)
    return (b[0] + x * size, b[1] + y * size,
            b[0] + (x + 1) * size, b[1] + (y + 1) * size)


def stage_index():
    from shapely.ops import unary_union
    from shapely.geometry import box
    lines = trail_lines(3857)
    buf = unary_union(lines).buffer(SELECT_M * 1.466 + 60)
    index = {}
    for name in DATASETS:
        cache = os.path.join(WORK, "ept-cache", name)
        meta_p = os.path.join(cache, "ept.json")
        fetch("%s/%s/ept.json" % (EPT_BASE, name), meta_p)
        meta = json.load(open(meta_p))
        nodes = {}
        seen_files = set()
        stack = ["0-0-0-0"]
        while stack:
            wave = [k for k in stack if k not in seen_files]
            stack = []
            for k in wave:
                seen_files.add(k)

            def _get(hk):
                hp = os.path.join(cache, "hier", hk + ".json")
                fetch("%s/%s/ept-hierarchy/%s.json"
                      % (EPT_BASE, name, hk), hp)
                return hp

            # Small batches: a hanging request can only stall its
            # own batch, and progress stays visible.
            for i in range(0, len(wave), 256):
                batch = wave[i:i + 256]
                with ThreadPoolExecutor(max_workers=16) as ex:
                    paths = list(ex.map(_get, batch))
                for hp in paths:
                    hier = json.load(open(hp))
                    for key, val in hier.items():
                        nb = ept_node_box(meta, key)
                        if not box(*nb).intersects(buf):
                            continue
                        if val < 0:
                            stack.append(key)
                        elif val > 0:
                            nodes[key] = val
                log("%s: %d hierarchy files, %d nodes so far"
                    % (name, len(seen_files), len(nodes)))
        index[name] = {"meta_bounds": meta["bounds"],
                       "nodes": nodes}
        log("%s: %d data nodes in corridor, %d points" %
            (name, len(nodes), sum(nodes.values())))
    json.dump(index, open(os.path.join(WORK, "node-index.json"), "w"))
    tot = sum(sum(v["nodes"].values()) for v in index.values())
    log("index total: %d points in corridor nodes" % tot)


# ------------------------------------------------------------------
# Stage: dsm -- bin first-return maxima per chunk
# ------------------------------------------------------------------

def stage_dsm():
    import laspy
    from pyproj import Transformer
    from shapely.geometry import box as shp_box
    index = json.load(open(os.path.join(WORK, "node-index.json")))
    # Depth-cap decision support: EPT distributes points across
    # octree depths; downloading every node is the full cloud, but
    # a depth cap trades a uniformly-thinned subset (max-per-cell
    # is robust in canopy) for a bounded file count. The cap is
    # chosen from these stats and passed as LIDAR_DEPTH_CAP.
    from collections import Counter
    by_depth = Counter()
    pts_depth = Counter()
    for rec in index.values():
        for key, n in rec["nodes"].items():
            d = int(key.split("-")[0])
            by_depth[d] += 1
            pts_depth[d] += n
    cum_n = cum_p = 0
    for d in sorted(by_depth):
        cum_n += by_depth[d]
        cum_p += pts_depth[d]
        log("depth <= %d: %d files, %d points cumulative" %
            (d, cum_n, cum_p))
    cap = os.environ.get("LIDAR_DEPTH_CAP")
    if cap:
        cap = int(cap)
        for name in index:
            index[name]["nodes"] = {
                k: v for k, v in index[name]["nodes"].items()
                if int(k.split("-")[0]) <= cap}
        log("LIDAR_DEPTH_CAP=%d applied: %d files remain" %
            (cap, sum(len(r["nodes"]) for r in index.values())))
    slots = band_chunks()
    log("chunks to fill: %d" % len(slots))
    t_fwd = Transformer.from_crs(3857, 6344, always_xy=True)
    os.makedirs(os.path.join(WORK, "chunks"), exist_ok=True)

    # Node -> datasets/boxes (in 6344) for chunk assignment.
    node_boxes = []  # (name, key, box6344)
    for name, rec in index.items():
        meta = {"bounds": rec["meta_bounds"]}
        for key in rec["nodes"]:
            b = ept_node_box(meta, key)
            corners = [t_fwd.transform(b[0], b[1]),
                       t_fwd.transform(b[2], b[1]),
                       t_fwd.transform(b[0], b[3]),
                       t_fwd.transform(b[2], b[3])]
            xs = [c[0] for c in corners]
            ys = [c[1] for c in corners]
            node_boxes.append((name, key,
                               (min(xs), min(ys), max(xs), max(ys))))

    def download(job):
        # Never raise: one bad file must not kill the batch (a
        # single IncompleteRead did exactly that on 2026-11-11,
        # aborting the stage at 6,228 of 15,557 files).
        name, key = job
        dest = os.path.join(WORK, "ept-cache", name, "laz", key + ".laz")
        try:
            return (job, fetch("%s/%s/ept-data/%s.laz"
                               % (EPT_BASE, name, key), dest), None)
        except Exception as e:  # noqa: BLE001
            return (job, 0, str(e))

    jobs = sorted({(n, k) for n, k, _ in node_boxes})
    log("EPT chunks to download: %d" % len(jobs))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=40) as ex:
        results = list(ex.map(download, jobs))
    failed = [j for j, _s, err in results if err]
    total_bytes = sum(s for _j, s, _e in results)
    if failed:
        log("%d downloads failed; retrying once" % len(failed))
        with ThreadPoolExecutor(max_workers=8) as ex:
            results2 = list(ex.map(download, failed))
        total_bytes += sum(s for _j, s, _e in results2)
        failed = [j for j, _s, err in results2 if err]
    if failed:
        log("WARNING: %d EPT files still missing after retry "
            "(their cells stay empty): %s" % (len(failed), failed[:10]))
        json.dump([list(j) for j in failed],
                  open(os.path.join(WORK, "dsm-missing.json"), "w"))
    log("downloaded %.2f GB in %.0fs (%d files ok, %d missing)" %
        (total_bytes / 1e9, time.time() - t0,
         len(jobs) - len(failed), len(failed)))

    import rasterio
    from rasterio.transform import from_origin
    total_pts = 0
    for (cx, cy) in slots:
        cb = chunk_bounds(cx, cy)
        dsm = np.full((CHUNK, CHUNK), np.nan, dtype=np.float32)
        flat = dsm.ravel()
        cbox = shp_box(*cb)
        todo = [(n, k) for n, k, b in node_boxes
                if shp_box(*b).intersects(cbox)]
        for name, key in todo:
            path = os.path.join(WORK, "ept-cache", name, "laz",
                                key + ".laz")
            if not os.path.exists(path):
                continue
            try:
                f_ctx = laspy.open(path)
            except Exception as e:  # noqa: BLE001
                log("skip unreadable %s: %s" % (path, e))
                continue
            with f_ctx as f:
                for pts in f.chunk_iterator(4_000_000):
                    rn = np.asarray(pts.return_number)
                    cl = np.asarray(pts.classification)
                    m = (rn == 1)
                    for nc in NOISE_CLASSES:
                        m &= cl != nc
                    if not m.any():
                        continue
                    x, y = t_fwd.transform(
                        np.asarray(pts.x)[m], np.asarray(pts.y)[m])
                    z = np.asarray(pts.z)[m]
                    keep = ((x >= cb[0]) & (x < cb[2]) &
                            (y >= cb[1]) & (y < cb[3]))
                    if not keep.any():
                        continue
                    x, y, z = x[keep], y[keep], z[keep]
                    col = (x - cb[0]).astype(np.int64)
                    row = (cb[3] - y).astype(np.int64)
                    # fmax, NOT maximum: maximum propagates the
                    # NaN fill value and no cell would ever fill
                    # (caught live 2026-11-11: chunks at 0.0%).
                    np.fmax.at(flat, row * CHUNK + col,
                               z.astype(np.float32))
                    total_pts += len(z)
        out = os.path.join(WORK, "chunks",
                           "dsm-%d-%d.tif" % (cx, cy))
        filled = int(np.isfinite(dsm).sum())
        if filled:
            with rasterio.open(
                    out, "w", driver="GTiff", width=CHUNK,
                    height=CHUNK, count=1, dtype="float32",
                    crs=CRS_LIDAR,
                    transform=from_origin(cb[0], cb[3], CELL, CELL),
                    nodata=np.nan, compress="deflate") as ds:
                ds.write(dsm, 1)
        log("chunk %d,%d: %d nodes, %.1f%% cells filled" %
            (cx, cy, len(todo), 100.0 * filled / CHUNK ** 2))
    log("DSM points binned: %d" % total_pts)


# ------------------------------------------------------------------
# Stage: dtm (+ chm / surface derivation)
# ------------------------------------------------------------------

def write_tif(path, arr, cb):
    import rasterio
    from rasterio.transform import from_origin
    with rasterio.open(
            path, "w", driver="GTiff", width=arr.shape[1],
            height=arr.shape[0], count=1, dtype="float32",
            crs=CRS_LIDAR,
            transform=from_origin(cb[0], cb[3], CELL, CELL),
            nodata=np.nan, compress="deflate") as ds:
        ds.write(arr.astype(np.float32), 1)


def stage_dtm():
    import rasterio
    from rasterio.windows import from_bounds
    slots = band_chunks()
    failed = []
    for (cx, cy) in slots:
        cb = chunk_bounds(cx, cy)
        dst = os.path.join(WORK, "chunks",
                           "dtm-%d-%d.tif" % (cx, cy))
        if os.path.exists(dst):
            continue
        # One remote tile fetch returning 0 bytes inside the VRT
        # read kills the whole stage (2026-11-11, chunk after
        # 11,4: TIFFFillTile got 0 bytes) -- retry each chunk with
        # a fresh VRT handle; record and continue on total failure.
        a = None
        for attempt in range(3):
            try:
                with rasterio.open(DEM_VRT) as vrt:
                    w = from_bounds(*cb, vrt.transform)
                    a = vrt.read(
                        1, window=w, out_shape=(CHUNK, CHUNK),
                        resampling=rasterio.enums.Resampling.bilinear)
                break
            except Exception as e:  # noqa: BLE001
                log("dtm chunk %d,%d read attempt %d failed: %s"
                    % (cx, cy, attempt + 1, e))
                time.sleep(15 * (attempt + 1))
        if a is None:
            log("dtm chunk %d,%d FAILED after 3 attempts; skipped"
                % (cx, cy))
            failed.append([cx, cy])
            continue
        a = a.astype(np.float32)
        a[a <= -9999] = np.nan
        write_tif(dst, a, cb)
        log("dtm chunk %d,%d read" % (cx, cy))
    if failed:
        json.dump(failed, open(os.path.join(WORK, "dtm-missing.json"),
                               "w"))
        log("dtm chunks missing after retries: %s" % (failed,))
    # Derive CHM + shade surface per chunk.
    for (cx, cy) in slots:
        dp = os.path.join(WORK, "chunks", "dsm-%d-%d.tif" % (cx, cy))
        tp = os.path.join(WORK, "chunks", "dtm-%d-%d.tif" % (cx, cy))
        if not (os.path.exists(dp) and os.path.exists(tp)):
            continue
        cb = chunk_bounds(cx, cy)
        with rasterio.open(dp) as ds:
            dsm = ds.read(1)
        with rasterio.open(tp) as ds:
            dtm = ds.read(1)
        chm = np.where(np.isfinite(dsm), dsm - dtm, 0.0)
        chm = np.clip(chm, 0, None).astype(np.float32)
        chm[~np.isfinite(dtm)] = np.nan
        write_tif(os.path.join(WORK, "chunks",
                               "chm-%d-%d.tif" % (cx, cy)), chm, cb)
        surf = np.where(np.isfinite(dsm), dsm, dtm).astype(np.float32)
        write_tif(os.path.join(WORK, "chunks",
                               "surf-%d-%d.tif" % (cx, cy)), surf, cb)
    log("dtm + chm + surf derived for %d slots" % len(slots))


# ------------------------------------------------------------------
# Stage: tiles
# ------------------------------------------------------------------

RAMP_STOPS = [  # (height m, (r, g, b)) -- pale ground -> deep green
    (0.0, (233, 225, 199)), (2.0, (205, 216, 152)),
    (5.0, (164, 201, 116)), (9.0, (110, 176, 92)),
    (14.0, (64, 145, 72)), (19.0, (34, 110, 55)),
    (25.0, (18, 82, 40)), (32.0, (12, 64, 30)),
]


def ramp_lut():
    hs = np.array([s[0] for s in RAMP_STOPS])
    cs = np.array([s[1] for s in RAMP_STOPS], dtype=np.float64)
    xs = np.linspace(0, 32, 257)
    lut = np.stack([np.interp(xs, hs, cs[:, i]) for i in range(3)],
                   axis=1).astype(np.uint8)
    return lut


def hillshade(surf, cell_ground_m, az_deg=315.0, alt_deg=45.0):
    gy, gx = np.gradient(surf, cell_ground_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gy, gx)
    az = math.radians(360.0 - az_deg + 90.0)
    alt = math.radians(alt_deg)
    sh = (np.sin(alt) * np.cos(slope) +
          np.cos(alt) * np.sin(slope) * np.cos(az - aspect))
    return np.clip(sh, 0, 1)


def build_vrt(kind, slots):
    """Hand-written GDAL VRT over the chunk GeoTIFFs of one kind
    (all chunks share the 1 m EPSG:6344 grid, so sources are
    simple). Returns path."""
    import rasterio
    from rasterio.transform import from_origin
    minx = min(chunk_bounds(cx, cy)[0] for cx, cy in slots)
    miny = min(chunk_bounds(cx, cy)[1] for cx, cy in slots)
    maxx = max(chunk_bounds(cx, cy)[2] for cx, cy in slots)
    maxy = max(chunk_bounds(cx, cy)[3] for cx, cy in slots)
    W = int((maxx - minx) / CELL)
    H = int((maxy - miny) / CELL)
    tr = from_origin(minx, maxy, CELL, CELL)
    lines = [
        '<VRTDataset rasterXSize="%d" rasterYSize="%d">' % (W, H),
        '  <SRS dataAxisToSRSAxisMapping="1,2">EPSG:6344</SRS>',
        '  <GeoTransform>%s</GeoTransform>' %
        ", ".join(repr(v) for v in tr.to_gdal()),
        '  <VRTRasterBand dataType="Float32" band="1">',
        '    <NoDataValue>nan</NoDataValue>',
    ]
    for (cx, cy) in slots:
        p = os.path.join(WORK, "chunks",
                         "%s-%d-%d.tif" % (kind, cx, cy))
        if not os.path.exists(p):
            continue
        cb = chunk_bounds(cx, cy)
        dx = int((cb[0] - minx) / CELL)
        dy = int((maxy - cb[3]) / CELL)
        lines += [
            '    <SimpleSource>',
            '      <SourceFilename relativeToVRT="1">%s'
            '</SourceFilename>' %
            os.path.relpath(p, WORK),
            '      <SourceBand>1</SourceBand>',
            '      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d"/>'
            % (CHUNK, CHUNK),
            '      <DstRect xOff="%d" yOff="%d" xSize="%d" ySize="%d"/>'
            % (dx, dy, CHUNK, CHUNK),
            '    </SimpleSource>',
        ]
    lines += ['  </VRTRasterBand>', '</VRTDataset>']
    path = os.path.join(WORK, "%s.vrt" % kind)
    open(path, "w").write("\n".join(lines))
    with rasterio.open(path) as ds:
        assert ds.width == W and ds.height == H
    return path


def stage_tiles():
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.crs import CRS
    from rasterio.transform import from_bounds as tf_bounds
    from shapely.ops import unary_union
    from PIL import Image
    slots = band_chunks()
    surf_vrt = build_vrt("surf", slots)
    chm_vrt = build_vrt("chm", slots)
    band3857 = unary_union(trail_lines(3857)).buffer(BAND_M * 1.466)
    lut = ramp_lut()
    out_root = os.path.join(ROOT, "site", "tiles")
    stats = {}
    T = 256
    for z in range(9, 17):
        n = 2 ** z
        world = 2 * 20037508.342789244
        tile_m = world / n
        bx = band3857.bounds
        tx0 = int((bx[0] + world / 2) / tile_m)
        tx1 = int((bx[2] + world / 2) / tile_m)
        ty0 = int((world / 2 - bx[3]) / tile_m)
        ty1 = int((world / 2 - bx[1]) / tile_m)
        count = {"canopy-shade": 0, "canopy-height": 0}
        byt = {"canopy-shade": 0, "canopy-height": 0}
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                x0 = -world / 2 + tx * tile_m
                x1 = x0 + tile_m
                y1 = world / 2 - ty * tile_m
                y0 = y1 - tile_m
                from shapely.geometry import box as shp_box
                if not shp_box(x0, y0, x1, y1).intersects(band3857):
                    continue
                dst_tr = tf_bounds(x0, y0, x1, y1, T, T)
                cell_ground = tile_m / T * 0.682  # 3857->ground @47N
                for kind, vrt in (("surf", surf_vrt),
                                  ("chm", chm_vrt)):
                    arr = np.full((T, T), np.nan, dtype=np.float32)
                    with rasterio.open(vrt) as ds:
                        reproject(
                            source=rasterio.band(ds, 1),
                            destination=arr,
                            dst_transform=dst_tr,
                            dst_crs=CRS.from_epsg(3857),
                            src_nodata=np.nan, dst_nodata=np.nan,
                            resampling=(Resampling.bilinear
                                        if kind == "surf" else
                                        Resampling.average))
                    if kind == "surf":
                        valid = np.isfinite(arr)
                        if not valid.any():
                            continue
                        fill = np.where(valid, arr,
                                        np.nanmean(arr[valid]))
                        sh = hillshade(fill, cell_ground)
                        grey = (255 * sh).astype(np.uint8)
                        la = np.dstack(
                            [grey,
                             np.where(valid, 255, 0).astype(np.uint8)])
                        img = Image.fromarray(la, "LA")
                        name = "canopy-shade"
                    else:
                        valid = np.isfinite(arr)
                        if not valid.any():
                            continue
                        idx = np.clip(
                            (np.where(valid, arr, 0) / 32.0 * 256),
                            0, 256).astype(np.int32)
                        rgb = lut[idx]
                        rgba = np.dstack(
                            [rgb, np.where(valid, 255, 0).astype(np.uint8)])
                        img = Image.fromarray(rgba, "RGBA")
                        name = "canopy-height"
                    d = os.path.join(out_root, name, str(z), str(tx))
                    os.makedirs(d, exist_ok=True)
                    p = os.path.join(d, "%d.png" % ty)
                    img.save(p, optimize=True)
                    count[name] += 1
                    byt[name] += os.path.getsize(p)
        stats[z] = {k: (count[k], byt[k]) for k in count}
        log("z%d tiles: shade %d (%.1f MB), height %d (%.1f MB)" %
            (z, count["canopy-shade"], byt["canopy-shade"] / 1e6,
             count["canopy-height"], byt["canopy-height"] / 1e6))
    json.dump(stats, open(os.path.join(WORK, "tile-stats.json"), "w"),
              indent=1)


# ------------------------------------------------------------------
# Stage: check -- sample spots
# ------------------------------------------------------------------

def _win_means(a, w):
    """Mean of every w x w window (stride 10) via integral image."""
    ii = np.zeros((a.shape[0] + 1, a.shape[1] + 1), dtype=np.float64)
    ii[1:, 1:] = np.cumsum(np.cumsum(a, axis=0), axis=1)
    s = (ii[w:, w:] - ii[:-w, w:] - ii[w:, :-w] + ii[:-w, :-w])
    return s / (w * w)


def stage_check():
    import rasterio
    from PIL import Image
    slots = band_chunks()
    best_stand, best_clear = None, None
    W = 60    # inner window (m)
    R = 300   # context window (m) for the clearing test
    for (cx, cy) in slots:
        p = os.path.join(WORK, "chunks", "chm-%d-%d.tif" % (cx, cy))
        if not os.path.exists(p):
            continue
        with rasterio.open(p) as ds:
            chm = ds.read(1)
        valid = np.isfinite(chm)
        if valid.sum() < R * R:
            continue
        a = np.where(valid, chm, 0.0)
        # Evaluate on a stride-10 lattice using integral images at
        # full resolution but only the lattice points.
        inner = _win_means(a, W)[::10, ::10]
        outer = _win_means(a, R)[::10, ::10]
        # Align the lattices: inner lattice index i (window start
        # 10i) shares a centre with outer lattice index i-oi, where
        # oi = (R-W)/2/10. The old slice assumed equal sizes, so
        # the shape check skipped every chunk (both candidates None
        # on the first run, 2026-11-11).
        oi = (R - W) // 2 // 10
        n = outer.shape[0]
        inner_a = inner[oi:oi + n, oi:oi + n]
        oc = outer
        si = np.unravel_index(np.argmax(inner_a), inner_a.shape)
        if best_stand is None or inner_a[si] > best_stand[0]:
            best_stand = (float(inner_a[si]), int(cx), int(cy),
                          int((si[1] + oi) * 10),
                          int((si[0] + oi) * 10))
        # Clearing: bare inner window inside standing forest.
        score = np.where((inner_a <= 2.0) & (oc >= 8.0),
                         oc - inner_a, -1)
        ci = np.unravel_index(np.argmax(score), score.shape)
        if score[ci] > 0 and (best_clear is None or
                              score[ci] > best_clear[0]):
            best_clear = (float(inner_a[ci]), int(cx), int(cy),
                          int((ci[1] + oi) * 10),
                          int((ci[0] + oi) * 10),
                          float(oc[ci]))
    log("stand candidate (60 m mean, m): %s" % (best_stand,))
    log("clear candidate (inner mean, chunk, x, y, context mean): "
        "%s" % (best_clear,))
    # Render 600 m sample sheets for both products at both spots.
    samples = os.path.join(WORK, "samples")
    os.makedirs(samples, exist_ok=True)
    lut = ramp_lut()
    for label, cand in (("stand", best_stand), ("clear", best_clear)):
        if cand is None:
            continue
        cx, cy, px, py = cand[1], cand[2], cand[3], cand[4]
        cb = chunk_bounds(cx, cy)
        cxm = cb[0] + px + 30
        cym = cb[3] - (py + 30)
        for kind in ("surf", "chm"):
            p = os.path.join(WORK, "chunks",
                             "%s-%d-%d.tif" % (kind, cx, cy))
            with rasterio.open(p) as ds:
                a = ds.read(1)
            x0 = int(max(0, px - 270))
            y0 = int(max(0, py - 270))
            win = a[y0:y0 + 600, x0:x0 + 600]
            if kind == "surf":
                sh = hillshade(np.where(np.isfinite(win), win,
                                        np.nanmean(win)), 1.0)
                img = Image.fromarray((255 * sh).astype(np.uint8))
            else:
                idx = np.clip((np.nan_to_num(win) / 32.0 * 256),
                              0, 256).astype(np.int32)
                img = Image.fromarray(lut[idx], "RGB")
            img = img.resize((600, 600), Image.NEAREST)
            img.save(os.path.join(
                samples, "sample-%s-%s.png" % (label, kind)))
        with rasterio.open(os.path.join(
                WORK, "chunks", "chm-%d-%d.tif" % (cx, cy))) as ds:
            chm = ds.read(1)
        win = chm[int(max(0, py - 270)):int(py + 330),
                  int(max(0, px - 270)):int(px + 330)]
        log("%s spot: centre UTM %.0f,%.0f  CHM mean %.1f m  "
            "p95 %.1f m  max %.1f m  (600 m window)" %
            (label, cxm, cym, float(np.nanmean(win)),
             float(np.nanpercentile(win, 95)),
             float(np.nanmax(win))))
    json.dump({"stand": best_stand, "clear": best_clear},
              open(os.path.join(WORK, "sample-spots.json"), "w"))


STAGES = {"index": stage_index, "dsm": stage_dsm, "dtm": stage_dtm,
          "tiles": stage_tiles, "check": stage_check}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(WORK, exist_ok=True)
    if which == "all":
        for s in ("index", "dsm", "dtm", "tiles", "check"):
            timed(s, STAGES[s])
    else:
        timed(which, STAGES[which])

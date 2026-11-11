# 2022 LiDAR trio — build report (Nov 11, 2026)

Paul's plan: run the CURRENT (2022, second-generation) trio first and
measure its real cost; the 2010/change-strip extension is NOT part of
this build. Two new bases join the Relief group next to "MN LiDAR
Hillshade": **MN LiDAR Canopy** (grey hillshade of the first-return
surface, DSM 2022) and **Canopy height (LiDAR)** (CHM = DSM − DTM,
colour ramp pale ground → deep green at 25 m+). Bare earth already
existed as the MnGeo WMS hillshade and was not rebuilt.

Pipeline: `scripts/build_lidar_trio.py` (stages `index | dsm | dtm |
tiles | check`), rerunnable, no hand steps. Supervisor
`working/lidar-trio/run_stage.sh <stage>` relaunches a stage if the
long job dies (needed — see friction 9). Tooling lives in
`working/lidar-trio/pylibs` (pip wheels); everything under
`working/lidar-trio/` is gitignored scratch.

## Cost table (measured Nov 11, 2026, UTC)

Clean-run stage timings (from `working/lidar-trio/stage-timings.json`):

| Stage | Wall clock | What it did |
|---|---|---|
| index | 455.5 s | Traversed the EPT hierarchies; 97,097 nodes / 4.934B points in the corridor selection band (Becker 25,565 nodes / 1.406B pts; UpperMiss WU4 71,523 / 3.528B — carries nearly all the Upper Mississippi corridor; WU2 2 nodes; WU5 7; WU6 0). Depth ≤10: 15,557 files / 1.159B pts (~24% uniform subset, ~4 first returns/m²). |
| dsm | 1,231.8 s | Downloaded + binned first returns (max per 1 m cell, EPSG:6344, noise classes 7/18 out): 561.9M points binned into 75 chunk GeoTIFFs (84 slots; 9 edge slots empty). Download phase inside this: 8.1 GB / 15,557 LAZ files in 1,878 s; 525 files failed first pass, all recovered on retry. |
| dtm | 1,650.1 s | Read the seamless gen-2 DEM VRT windowed per chunk at 1 m (84 chunks) + derived CHM and shade-surface chunks (75 each). |
| tiles | 1,343.8 s | Rendered PNG tiles z9–16, both products. |
| check | 168.1 s | Sample stand + clearing search and sample sheets. |
| **Total, clean runs** | **4,849.3 s (~81 min)** | |

Total elapsed for the build day including restarts, crashes, and
diagnosis was ~3 h 20 min (14:02–17:22 UTC). The difference is the
friction below, not the pipeline's steady-state cost. A from-scratch
rerun with the cache warm (LAZ + chunks on disk) would be the
clean-run total; a cold rerun adds the 1,878 s download and the
455 s index.

## Tile payload (shipped)

Shipped range is **z9–15**: 1,060 tiles, **82.7 MB** total — 530 shade
tiles / 31.1 MB and 530 height tiles / 51.6 MB. Per zoom (both
products): z9 8 tiles / 0.05 MB; z10 12 / 0.17 MB; z11 28 / 0.62 MB;
z12 54 / 1.94 MB; z13 120 / 6.00 MB; z14 250 / 18.14 MB; z15 588 /
55.75 MB. Per-zoom render time was flat at ~2–2.5 min/zoom.

**z16 was rendered, measured, and dropped:** 1,466 more tiles for
152.5 MB (shade 733 / 51.9 MB; height 733 / 100.6 MB) — it would have
taken the pair to 235 MB, past the tens-of-MB class the brief asked
for. `maxNativeZoom` is 15 in `site/app.js`; deeper zooms upscale
the z15 tiles. The z16 cost stays measured here so the cap can be
revisited with a number attached.

## Data volumes fetched

- EPT LAZ (public S3 `usgs-lidar-public`): 8.1 GB, 15,557 files
  (depth ≤10 subset of the corridor clouds).
- EPT hierarchy JSONs (index stage): 4,271 files.
- DEM VRT reads: 84 windows of 5×5 km at 0.5 m native, resampled to
  1 m, streamed from the MnGeo blob — volume not metered by the
  tooling (rasterio reports no byte count); the read, not the bytes,
  was the cost (~38 s/chunk).
- On-disk scratch at end of build: EPT cache 7.6 GB, chunks 9.4 GB,
  pylibs 207 MB (all under `working/lidar-trio/`, gitignored).

## The DSM fork (for the record)

No published statewide gen-2 DSM derivative exists (MnGeo WMS has
122 layers, none canopy/DSM; the MnGeo blob `derivatives/` holds only
ground-model products). Route (a) — USGS block first-return DSM tiles
+ per-tile LAZ staged on rockyweb.usgs.gov — measured Nov 11 and
rejected: UA-gated bot wall, ~50 KB/s single stream, instant 429 on
parallel requests, one test tile arrived truncated. Route (b) taken:
the same USGS point clouds mirrored as Entwine EPT datasets on the
public S3 bucket `usgs-lidar-public` (Registry of Open Data), read
directly — datasets `MN_BeckerCo_1_2021` +
`MN_UpperMissRiver_{2,4,5,6}_B22` (units 1 and 3 do not intersect the
corridor). Full provenance in `SOURCES.md`.

## Friction list (plain sentences)

1. `apt-get install gdal-bin` failed — the apt mirror stalled
   indefinitely (a detached apt-get held the lists lock for minutes
   and had to be killed). Switched to pip wheels into
   `working/lidar-trio/pylibs`: rasterio 1.4.3 (GDAL 3.9.3), laspy
   2.7.0 + lazrs 0.8.2, shapely 2.0.7, pyproj 3.8.0, numpy 2.2.6,
   pillow 13.0.0, requests.
2. `/tmp` is a 512 MB tmpfs — pip overflowed it; TMPDIR had to point
   at the big disk. Unpinned numpy resolution failed; versions are
   pinned (numpy==2.2.6 works).
3. The egress proxy caps aggregate request rate at roughly 3–8
   files/s per hostname regardless of concurrency (16 workers, then
   40, no improvement). That rate, not bandwidth, set the download
   time.
4. A single `IncompleteRead` on one EPT chunk crashed the whole DSM
   stage (6,228 of 15,557 files in). Fixed: the downloader never
   raises — failures are collected, retried once, and reported
   (`dsm-missing.json` if any remain; this build: 0 missing).
5. `np.maximum.at` propagates NaN, so the DSM binning filled 0.0%
   of cells on the first full run — caught live from the chunk log,
   fixed to `np.fmax.at`. Chunk 0,0 went from 0.0% to 20.9% filled.
6. A VRT window read died on a remote tile fetch returning 0 bytes
   (`TIFFFillTile: Read error ... got 0 bytes`), killing the DTM
   stage at 46/84 chunks. Fixed: each chunk read retries 3× with a
   fresh VRT handle and records-and-continues on total failure.
   The failed chunk (11,5) read cleanly on resume — transient.
7. A detached DTM run died silently with no traceback (~16:15, at
   53/84 chunks; no OOM evidence). Mitigation: the supervisor loop
   `run_stage.sh` relaunches a stage until it exits 0 (max 10
   attempts). The DTM stage's resume logic (skip existing chunks)
   made the restart cheap.
8. The check stage's window-lattice alignment assumed equal array
   sizes after stride-10 subsampling, so the shape check skipped
   every chunk and both candidates came back None. Fixed by aligning
   on the shared lattice.
9. The check stage then crashed on its last line: `np.int64` is not
   JSON-serializable. Fixed with `int()` casts. Spot values below
   were reproduced identically across the two runs.
10. The tiles stage reprojects from the 1 m VRT per tile with no
    overviews; per-zoom time stayed flat (~2–2.5 min) because tile
    count grows ~2.3× per zoom while source windows shrink 4×. No
    optimization was needed, but a rerun could build overviews on
    the chunk GeoTIFFs if it ever gets slow.

## Sample checks (CHM, 1 m cells)

- **Mature stand:** 60 m mean **27.4 m**, centre UTM 329120,
  5224160 (chunk 5,4). 600 m window: mean 17.2 m, p95 30.9 m, max
  40.8 m. Sample sheets: `working/lidar-trio/samples/sample-stand-{chm,surf}.png`.
- **Clearing:** 60 m mean **1.26 m** inside a 300 m context mean of
  **13.3 m**, centre UTM 400970, 5205680 (chunk 20,1). 600 m window:
  mean 11.2 m, p95 22.6 m, max 25.4 m. Sample sheets:
  `working/lidar-trio/samples/sample-clear-{chm,surf}.png`.
- Both sheets were eyeballed: the stand sheet is dense deep-green
  canopy with pale openings and visible individual crowns; the
  clearing sheet shows large pale clearcuts/fields inside dark
  forest. The shade sheet is grey hillshade in the bare-earth
  register with crown texture.

## Coverage audit (along the depicted lines)

2,030 sample points, every 100 m along both depicted lines
(Itasca Moraine + Laurentian Lakes), CHM read at each point:
**90.0% finite** (1,826/2,030). Along-trail CHM: mean 12.0 m,
median 14.0 m, p90 21.6 m, max 34.3 m; <1 m (open ground/tread/
water) 19.2%; ≥20 m (mature canopy) 15.7%. Audit script:
`working/lidar-trio/audit_coverage.py` (results in
`coverage-audit.json`).

Two honest holes, both documented, neither a build failure:

1. **Northern loop, 138 points / 13.8 km** (chunks 4,5 + 5,5; lat
   47.154–47.174, just north of Itasca State Park): no 2022 canopy
   tiles. Becker County's block ends at y-grid 5224 there, and a
   TNM query over the hole returned 76 LPC items with **zero**
   Upper Mississippi B22 tiles — the B22 project simply does not
   extend that far north. The only coverage north of the Becker
   edge is the older RedRiver D23 block (different project, not
   2022 gen-2 Upper Mississippi), which this build deliberately
   did not mix in. The bare-earth hillshade WMS still covers the
   loop; the two new bases simply end at the Becker edge.
2. **One water crossing, 66 points** (Chip-10/Chip-11, Chippewa
   National Forest, ~NCT mi 233–236): the seamless DEM carries
   nodata over open water, so CHM is NaN there and the tiles have a
   small transparent gap. Filling it would need a re-derive +
   re-tile for one river crossing; left as is.

## Site wiring

- `site/app.js`: `mnCanopyShade` + `mnCanopyHeight` tile layers,
  chooser entries after "MN LiDAR Hillshade" (13 bases total).
  CASING_BY_BASE: Canopy = `relief`; Height = `photo` (saturated
  colour surface — white casing keeps trail/section lines legible
  over deep green). Neither is in the `/^Aerial/` imagery family,
  so the label flip stays off. `maxZoom: 18, maxNativeZoom: 15`.
- `SOURCES.md`: full provenance incl. the DSM fork, corridor rule,
  leaf-off caveat (2022 flown spring leaf-off: conifers true,
  hardwood heights slightly low, clearcut detection unaffected),
  attributions (MnGeo / Minnesota DNR).
- `site/README.md` + `site/index.html` Sources card updated.

## Rerun

```sh
cd ~/workspace/itasca-trail-map
PYTHONPATH=working/lidar-trio/pylibs python3 scripts/build_lidar_trio.py <stage>
# or supervised:
bash working/lidar-trio/run_stage.sh <stage>   # stages: index dsm dtm tiles check
```

`LIDAR_DEPTH_CAP=10` is the depth-cap decision (documented in
`SOURCES.md`). The DSM stage reuses the LAZ cache; the DTM stage
skips chunks already read; the tiles stage overwrites PNGs in place.

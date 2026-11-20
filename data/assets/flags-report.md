# Photo pipeline — flags report

Generated 2026-11-19T16:17:07 from `working/photos-inbox-2026-11-19`.

Scanned 54 photos: 52 new positioned (0 EXIF GPS, 52 GPX-matched) grouped into 25 new pins; 2 without a position (excluded); 0 excluded by excluded-photos.txt; 0 already known, carried over untouched. 127 pins total in the file.

## GPX matching

Track file: `Nov_19,_2026,_1_24_51_PM.gpx` — 517 points, 2026-11-19T19:24:58+00:00 to 2026-11-19T20:32:35+00:00 UTC; EXIF datetimes read as America/Chicago local time; bracketing-point gap limit 120 s.

52 photos matched to the track (largest offset to the nearest track point: 19 s); 2 photos had no usable match and were excluded — listed under 'No position' below. Matched pins carry gps_source="gpx" and gpx_offset_s; they are time-interpolated estimates, not device fixes.


## Photo grouping

25 new pins: 5 single-photo, 20 multi-photo. A photo joins a pin when it is within 60 s of the pin's first photo and within 5 m of it (measured from the first photo, so a group cannot chain away down the trail). Roles are by shoot order only — first shot front, second back, the rest detail — never by compass; the photos carry no camera direction. Grouping is a first pass: the chapter splits and merges pins through its classification interface, and the pipeline never re-judges them. New pins arrive as type UN with no condition; nothing is classified here.

Multi-photo groups (review these — a group can fuse two nearby posts, and a long run can split across groups):

- PXL_20261119_192542649.MP.jpg + 2 more (PXL_20261119_192542649.MP.jpg, PXL_20261119_192559061.jpg, PXL_20261119_192603446.jpg) — span 21 s, spread 5.0 m
- PXL_20261119_192607885.MP.jpg + 2 more (PXL_20261119_192607885.MP.jpg, PXL_20261119_192613163.MP.jpg, PXL_20261119_192623125.jpg) — span 16 s, spread 3.6 m
- PXL_20261119_192637250.jpg + 1 more (PXL_20261119_192637250.jpg, PXL_20261119_192642797.MP.jpg) — span 5 s, spread 2.6 m
- PXL_20261119_192651760.jpg + 1 more (PXL_20261119_192651760.jpg, PXL_20261119_192659812.jpg) — span 8 s, spread 1.4 m
- PXL_20261119_192715479.jpg + 1 more (PXL_20261119_192715479.jpg, PXL_20261119_192724489.jpg) — span 9 s, spread 4.7 m
- PXL_20261119_192848804.jpg + 1 more (PXL_20261119_192848804.jpg, PXL_20261119_192853937.jpg) — span 5 s, spread 4.6 m
- PXL_20261119_193013209.jpg + 1 more (PXL_20261119_193013209.jpg, PXL_20261119_193017764.jpg) — span 4 s, spread 3.0 m
- PXL_20261119_193358177.jpg + 2 more (PXL_20261119_193358177.jpg, PXL_20261119_193402609.jpg, PXL_20261119_193405001.jpg) — span 7 s, spread 3.4 m
- PXL_20261119_193407005.MP.jpg + 1 more (PXL_20261119_193407005.MP.jpg, PXL_20261119_193409238.MP.jpg) — span 2 s, spread 2.7 m
- PXL_20261119_193411365.jpg + 2 more (PXL_20261119_193411365.jpg, PXL_20261119_193413608.jpg, PXL_20261119_193419492.jpg) — span 8 s, spread 4.5 m
- PXL_20261119_193847356.MP.jpg + 1 more (PXL_20261119_193847356.MP.jpg, PXL_20261119_193853194.jpg) — span 6 s, spread 4.1 m
- PXL_20261119_193902454.jpg + 1 more (PXL_20261119_193902454.jpg, PXL_20261119_193908566.MP.jpg) — span 6 s, spread 4.5 m
- PXL_20261119_194148382.jpg + 1 more (PXL_20261119_194148382.jpg, PXL_20261119_194151549.jpg) — span 3 s, spread 2.1 m
- PXL_20261119_194156224.jpg + 2 more (PXL_20261119_194156224.jpg, PXL_20261119_194200348.MP.jpg, PXL_20261119_194204084.jpg) — span 8 s, spread 2.9 m
- PXL_20261119_194211909.MP.jpg + 2 more (PXL_20261119_194211909.MP.jpg, PXL_20261119_194216385.jpg, PXL_20261119_194223789.jpg) — span 12 s, spread 4.7 m
- PXL_20261119_194242601.jpg + 1 more (PXL_20261119_194242601.jpg, PXL_20261119_194245985.MP.jpg) — span 3 s, spread 2.7 m
- PXL_20261119_194249425.jpg + 1 more (PXL_20261119_194249425.jpg, PXL_20261119_194256061.jpg) — span 7 s, spread 4.9 m
- PXL_20261119_194715154.jpg + 1 more (PXL_20261119_194715154.jpg, PXL_20261119_194720383.MP.jpg) — span 5 s, spread 2.4 m
- PXL_20261119_195225482.jpg + 2 more (PXL_20261119_195225482.jpg, PXL_20261119_195226728.jpg, PXL_20261119_195239728.MP.jpg) — span 14 s, spread 3.8 m
- PXL_20261119_195927805.MP.jpg + 1 more (PXL_20261119_195927805.MP.jpg, PXL_20261119_195935023.jpg) — span 8 s, spread 0.7 m

## No position — excluded from the map

- PXL_20261119_171954506.jpg — photographer: PJM
- PXL_20261119_203242751.MP.jpg — photographer: PJM

## GPS but no camera direction (informational)

These photos carry GPS and were pinned, but no valid EXIF camera direction (GPS ImgDirection) — their pins have null direction fields. Not an error.

- PXL_20261119_192510528.jpg — photographer: PJM
- PXL_20261119_192531559.jpg — photographer: PJM
- PXL_20261119_192542649.MP.jpg — photographer: PJM
- PXL_20261119_192559061.jpg — photographer: PJM
- PXL_20261119_192603446.jpg — photographer: PJM
- PXL_20261119_192607885.MP.jpg — photographer: PJM
- PXL_20261119_192613163.MP.jpg — photographer: PJM
- PXL_20261119_192623125.jpg — photographer: PJM
- PXL_20261119_192637250.jpg — photographer: PJM
- PXL_20261119_192642797.MP.jpg — photographer: PJM
- PXL_20261119_192651760.jpg — photographer: PJM
- PXL_20261119_192659812.jpg — photographer: PJM
- PXL_20261119_192715479.jpg — photographer: PJM
- PXL_20261119_192724489.jpg — photographer: PJM
- PXL_20261119_192848804.jpg — photographer: PJM
- PXL_20261119_192853937.jpg — photographer: PJM
- PXL_20261119_192900435.MP.jpg — photographer: PJM
- PXL_20261119_193013209.jpg — photographer: PJM
- PXL_20261119_193017764.jpg — photographer: PJM
- PXL_20261119_193023449.jpg — photographer: PJM
- PXL_20261119_193358177.jpg — photographer: PJM
- PXL_20261119_193402609.jpg — photographer: PJM
- PXL_20261119_193405001.jpg — photographer: PJM
- PXL_20261119_193407005.MP.jpg — photographer: PJM
- PXL_20261119_193409238.MP.jpg — photographer: PJM
- PXL_20261119_193411365.jpg — photographer: PJM
- PXL_20261119_193413608.jpg — photographer: PJM
- PXL_20261119_193419492.jpg — photographer: PJM
- PXL_20261119_193847356.MP.jpg — photographer: PJM
- PXL_20261119_193853194.jpg — photographer: PJM
- PXL_20261119_193902454.jpg — photographer: PJM
- PXL_20261119_193908566.MP.jpg — photographer: PJM
- PXL_20261119_194148382.jpg — photographer: PJM
- PXL_20261119_194151549.jpg — photographer: PJM
- PXL_20261119_194156224.jpg — photographer: PJM
- PXL_20261119_194200348.MP.jpg — photographer: PJM
- PXL_20261119_194204084.jpg — photographer: PJM
- PXL_20261119_194211909.MP.jpg — photographer: PJM
- PXL_20261119_194216385.jpg — photographer: PJM
- PXL_20261119_194223789.jpg — photographer: PJM
- PXL_20261119_194242601.jpg — photographer: PJM
- PXL_20261119_194245985.MP.jpg — photographer: PJM
- PXL_20261119_194249425.jpg — photographer: PJM
- PXL_20261119_194256061.jpg — photographer: PJM
- PXL_20261119_194715154.jpg — photographer: PJM
- PXL_20261119_194720383.MP.jpg — photographer: PJM
- PXL_20261119_195225482.jpg — photographer: PJM
- PXL_20261119_195226728.jpg — photographer: PJM
- PXL_20261119_195239728.MP.jpg — photographer: PJM
- PXL_20261119_195927805.MP.jpg — photographer: PJM
- PXL_20261119_195935023.jpg — photographer: PJM
- PXL_20261119_203217269.jpg — photographer: PJM

## Chainage along the trail

25 pins snapped to the depicted chain (chainage_mi + section stamped); 0 off-chain (> 250 m — chainage / section null).


## Oversize refusals (> 5 MB output)

- none

## Duplicates (same datetime + coordinates)

- none

# Photoreal world textures

Higgsfield-generated (nano_banana / nano_banana_2), seamless-tiled top-down plates
used for the "believable cities" look. Recovered 2026-08-05 from the only copy that
still had them.

| file | px | what it is |
|---|---|---|
| `road_asphalt.jpg` | 512×512 | premium tarmac tile, brightened for the dark road |
| `city_hood.jpg` | 1024×1024 | drone-photo aerial city — rooftops, AC units, crosswalks, parked cars |
| `city_sf.jpg` | 1024×1024 | San Francisco row-house grid |
| `city_egypt.jpg` | 1024×1024 | Nile-valley town |
| `city_tokyo.jpg` | 1024×1024 | blue-hour night district |

## Why these are here, and why nothing references them yet

They were originally embedded as base64 data-URIs inside a **local-only** build
(`QMM-Games/QMM_Racing/index.html`, 2.3 MB) and were never committed. That build is
the flat top-down renderer and predates the pseudo-3D chase camera.

Audited 2026-08-05: these textures were **not** in this repo's history, and **not** in
the build itch was serving either — despite notes claiming the believable-cities build
had shipped. They existed on exactly one machine, in one uncommitted file. Hence this
folder.

Stored as real JPEGs rather than base64: ~33% smaller, and no ~600 KB of base64
bloating `index.html`.

## Wiring them into the chase camera is NOT a drop-in

The original code (`_cityGround()` / `_cityImg()` / `_roadPattern()`) tiled these flat
with `drawImage` under a top-down road. The chase camera's ground is in **perspective**,
and canvas2d is affine-only — the same wall documented in `NOTES-3D-RENDERER.md`. A
texture drawn with a plain transform will visibly swim.

The real approach is **Mode-7 style strip mapping**: slice the ground into horizontal
bands and scale each band by its depth. That is a render feature with a real cost on a
GPU-less rig, not a port. Budget it as such.

They drop straight into the **flat** renderer (camMode 1/2) with no such problem.

**Nothing references these files yet. Do not delete them as dead assets.**

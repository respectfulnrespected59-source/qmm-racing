# Quantum Motors — 3D chase renderer, working notes

Handoff notes for picking this up on the other rig. Everything lives in the single
`index.html`. Written 2026-08-05.

---

## There are TWO renderers

| | function | used by |
|---|---|---|
| flat top-down (original) | `draw()` | camMode 1 (BIRDS-EYE), 2 (CLOSE) |
| pseudo-3D chase | `draw3D()` | camMode 0 (CHASE) — **the default** |

`C` cycles them. The flat renderer is untouched and still works — it's the fallback
if anything in the 3D path goes wrong.

**Do not try to fake the chase view by transforming the flat renderer.** That was
tried first: rotate the world heading-up and squash Y with `ctx.scale`. It fails
because canvas2d is affine-only and cannot do perspective — the city lies flat, and
re-aiming the building extrusion just detaches the roofs into floating slabs.

---

## How draw3D works

Nothing uses `ctx.translate/scale` for the world. Every point goes through a pinhole
camera sitting behind and above the car, and geometry is emitted already in screen
space:

```
forward  f = (p − cam) · heading          scale s = focal / f
right    r = (p − cam) · heading⊥
screenX  = W/2 + r*s
screenY  = horizon + (camHeight − z) * s
```

`z` is height above the tarmac: road is `z=0`, a building roof is `z=h3d`.

**Core primitives**

- `p3(wx,wy,z)` — project one point. Writes `p3x/p3y/p3s`, returns forward distance.
  `p3s <= 0` means behind the lens.
- `p3Set(i,wx,wy,z)` + `p3Poly(n)` — load a polygon then clip it against the near
  plane (Sutherland–Hodgman, one plane) and emit it as a subpath. A quad can come
  out a pentagon; that's what happens to the road passing under the car.
- `p3Quad`, `p3Ellipse`, `p3RectG`, `p3Box` — convenience wrappers.
- `p3Strip` / `p3Wall` / `p3RangeStrip` — road surface, kerb walls, and fixed-index
  strips (river, overpass deck, jump ramp).
- `p3Billboard(x,y,artFn,k)` — anchors flat art on the ground and lets perspective
  scale it. `k` is needed because the original roadside art was never drawn to world
  scale; current values: crowd 1.9, deco 3.2, lamps 3.0, park trees 2.8.

**Cars** map their top-down sprite through a *projected affine basis*: project the
roof centre, then one probe forward and one right, and those two screen deltas
become the sprite's x/y axes. So the art lies on the car's real roof plane. The
forward probe samples at the pitched nose height, which is what makes the body lean
back under power. A short box under it gives volume, and the rear face carries
panel / bumper / tail lights.

---

## The camera rig

```js
const CAM_H = 400, CAM_BACK = 545, CAM_CARY = 0.80;
```

- `CAM_H` — height above the tarmac. **`CAM_H / CAM_BACK` is the angle** and is the
  number that actually matters. 0.73 currently: high and near-overhead, keeping the
  elevated feel of the original top-down while perspective runs the road to a horizon.
- `CAM_BACK` — how far behind the car.
- `CAM_CARY` — where the car sits vertically in frame. **The horizon is derived from
  this**, so the car stays planted at any window size.

Do NOT expose the horizon as a direct dial — it fights the height dial (raise the
camera and the car falls off the bottom of the screen). That was tried and replaced.

Lower angle = you see the car's side walls and it reads as a box. Higher angle = you
see the roof. 0.73 is where it landed after several rounds.

---

## Gotchas that cost real time

**Near-plane slivers on transverse geometry.** Anything spanning the road sideways —
checkpoint gates, the finish band, bridge towers — must be culled on its **nearest
end**, not its centre:

```js
const f = Math.min(f_leftEnd, f_rightEnd);
```

On a curving track a gate can sit centre-ahead with one post already behind the lens,
and clipping stretches that quad into a thin streak across the whole screen. This
showed up as a mystery gold diagonal for several iterations. It was isolated by
freezing the camera and nulling one layer at a time — worth repeating for any future
visual mystery rather than guessing.

**Buildings occluding the car.** The lens trails 545 units behind along the car's
heading, so hugging a kerb puts it right next to that side's buildings. One of those,
being nearer than the car, sorts on top and slices the car in half. Distance culling
alone does not fix it — it needs the **lateral** test too. Buildings are only dropped
when they're *both* close and dead ahead.

**Skid marks were invisible** because they were `#08080d` on a `#141026` road — black
on near-black. They now get a lighter scuff halo plus a darker core. If any decal
seems to be "not drawing", check its contrast against the road before debugging.

**Emit trails by distance, not per frame.** At 60fps a per-frame emitter lays ~120
marks/sec, which is hundreds of clipped polygons to re-project every frame for a trail
that already overlaps itself. Every ~11 units is plenty.

---

## Performance

Measured on this rig's Intel HD 620 at 1280×720:

| | before | after |
|---|---|---|
| frame interval p50 | 39 ms (26 fps) | ~16 ms (60 fps) |
| stutters over 50 ms | 22.5 % | ~0.2 % |

The 3D path is **faster** than the flat one, which is counter-intuitive but correct:
a chase camera only draws a cone in front of you and distant geometry is tiny.

What actually mattered, in order:
1. Real viewport culling — the flat renderer was drawing roughly 5× the visible world.
2. Draw-call batching — window quads grouped by colour, ~7× fewer calls per building.
3. Baking — storefront signs to sprites, road/kerb/crack geometry to `Path2D`.
4. Killing per-frame allocation (the kerb loop was making 442 objects a frame).
5. Aerial-perspective fog cache is nested `Map→Map→Array`, not string keys — it runs
   four times per building per frame.

There's an **adaptive governor** (`PERF`, `perfSample`) that watches the delivered
frame interval and sheds bloom → detail radius → render scale on rigs that can't keep
up, then climbs back. It only touches internal knobs, never the player's `gfxTier`.

**Profiling method** (worth reusing): a script injects wrappers around every `draw*`
function into a temporary copy of `index.html`, drives the game with Playwright, and
reports per-subsystem cost plus the real `requestAnimationFrame` gap. The rAF gap is
the number that matters — JS time can be fine while frames land 40 ms apart.

**Caveat:** don't trust profiler numbers while a browser tab is running the game on
the same machine. It shares the iGPU and skews everything. The tell is that *untouched*
subsystems slow by the same factor.

---

## Controls

Two schemes, toggled with `G`, persisted to `localStorage['qmCtrl2']`.

- **AUTO** — default and what the game is tuned around: always accelerating, hold
  `SPACE` to drift.
- **MANUAL** — `SPACE` is throttle; blip it off and back on within 260 ms to latch a
  held drift. Tried and set aside as not fitting the feel. Nothing in the UI points
  at it. Kept in case it's wanted again.

Note if revisiting: counting two taps does *not* work, because you enter corners
already holding the throttle — that makes a "double tap" into release-tap-release-tap,
three motions mid-corner. Measuring the throttle-*off* duration is what made it
drivable.

---

## UHD polish pass — 2026-08-05, second rig

Added on top of the chase renderer. Nothing here changed the camera rig or the flat
renderer's structure.

**Surfaces.** The tarmac was a single flat fill, which reads as a painted colour rather
than a surface. It now stacks: a cached screen-space depth ramp (`roadSheen`),
transverse slab seams (`p3Seams` — seams flicking past are a large part of why speed
reads as speed), longitudinal pour lines, kerb grime, and a racing line built as a dark
core inside a lighter sheen halo, because rubbered-in tarmac is *polished*, not merely
darker.

**Buildings.** Every visible wall used to take the identical flat colour — that, not
the lack of texture, is why they read as paper cutouts. Faces now take a lambert term
against `SUN3`, a **fixed world-space key**. Do not tie it to the camera: a key that
swings as you steer makes every facade pulse, and it reads as flicker rather than as
light. Plus corner catch-lights, a sky-catch band up top, one extra batched pass for a
glass highlight on every window head, roof furniture to break the skyline, and a lit
ground-floor shopfront band.

**Cars.** Rear face rebuilt as slim Camaro-style clusters quartered by a dark cross.
The failed first attempt is the instructive part: lamps covering 48% of the face height
and 84% of its width, *plus* a body-colour accent band, *plus* a glow radius scaled off
the full body width, summed to a solid red box. Lamps must be a small bright accent on
a mostly dark tail. Body flanks take the same `SUN3` lambert plus a shoulder line where
flank meets roof — that highlight is the single cue separating glossy paint from a matte
block. **Rivals now have a brake signal** (`r._brk`, from real deceleration with a 0.22s
hold); before this, `braking` was hardcoded `isPlayer ? K.brake : false`, so tail lights
only ever lit on the one car you cannot see them on.

**Nitro flame.** The 3D path drew three axis-aligned ellipses that ignored `p.rot`
entirely, so the plume never pointed anywhere and read as bubbles. It is now tapered
world-space geometry along the exhaust axis — perspective orients and foreshortens it
for free. Length is deliberately generous: at the camera's 0.73 angle a physically-tidy
plume foreshortens into a flicker and has to overshoot to read.

**HUD.** One shared `hudPanel()` glass treatment across leaderboard, lap block,
speedometer and minimap. Gradients are cached and **invalidated on the resize event,
not inside `resize()`** — `resize()` is called immediately at its definition, long
before those caches are declared, and touching a `let`/`const` in its temporal dead
zone throws. (`typeof` does not save you there either.)

---

## The trap that cost the most time here

**`PERF.lvl` silently switches new effects off.** The governor climbs to 3+ on a
GPU-less / headless-SwiftShader rig and stays there, so anything written
`if(... && PERF.lvl < 3)` is simply never drawn. A brand-new effect then looks broken
while the code is perfectly correct: geometry verified, no JS error, nothing on screen.

The diagnostic that settles it in one shot — re-render at a loud colour and high alpha
(`#00ff00`, alpha 0.95). Still nothing means the **guard** is false, not the geometry;
then strip conditions one at a time. Do not keep re-reading the drawing code.

Standing rule from this: gate *garnish* on `PERF.lvl`, never gate *readability* on it.
Night headlight cones and the road depth-sheen were both wrongly gated and were
therefore invisible on exactly the weak rigs that need them most. `!lite` is the right
gate for those — `lite` is the player's explicit choice, the governor is not.

The same mistake has an LOD flavour: roof furniture gated to the *close* radius never
appeared, because a skyline silhouette is read at *distance*. Match the LOD radius to
the distance at which the feature is actually perceived.

**Measuring.** The first rAF sample after page load is a warm-up outlier — one build
measured p50 18.6 / p99 40.6 and settled to 17.0 / 22.0 over the next three runs. Take
3+ samples and discard the first. This box also drifts over a long session, so compare
builds **back to back via `git stash` in the same browser session**, never against a
number from an hour ago. Final for this pass: p50 16.7–17.6 ms, 0% frames over 50 ms,
against a pristine-HEAD p50 of 16.7 measured the same way. The p99 spikes appear
identically in both builds, so they are the machine, not the code.

---

## Still open

- **Landmarks**: `park`, `lake`, `gas`, `school` interiors are fairly plain in 3D —
  the stadium, pyramids, sphinx and Golden Gate got the most attention.
- **Night mode** is much closer now — headlight cones are ported and ground floors
  light up — but it has still had far less eyes-on than day.
- **Figure-8 / Cross-Country** tracks render their water, overpass and jump ramp, but
  haven't been driven end-to-end in chase view.
- The **flat renderer** still carries old top-down polish (flower checkpoints,
  turn-guide chevrons, wet reflection streaks) only partly carried over.
- **Menus / garage / results screens** were deliberately left out of the UHD pass.
- `rebuild-zip.py` hardcodes `os.chdir(r'C:\Users\respe\qmm-racing')`, which is not
  where the checkout lives on every rig. Fix the path before trusting it.
- All of the above was verified on headless SwiftShader, 3–5× slower than real Chrome.
  Judge the *look* on a real machine.

---

# ★ CARS ARE NO LONGER DRAWN — they are baked 3D turntables (2026-08-11)

Everything above about `p3Car` still exists, but it is now the **fallback**. A car with a strip in
`assets/cars3d/` is drawn as a pre-rendered frame of a real 3D mesh.

**Why this works here and nowhere else:** the rig's tilt never changes — `CAM_H/CAM_BACK` is a
constant 0.73 (36.3°). Only the car's *yaw* varies, so one 1-D strip of 48 frames covers every angle
you can ever see, for one `drawImage`. A free camera would need a 2-D grid and this would be absurd.
No GPU, no three.js in the shipped game, no second render path.

## The pipeline

| stage | where |
|---|---|
| meshes (CC-BY, Sketchfab) | `tools/bake3d/hi/<id>/scene.gltf` — **gitignored, ~470MB** |
| bake | `tools/bake3d/bake.html`, driven by Playwright |
| install + quantise | `tools/bake3d/install_strips.py <dump>` |
| runtime | `STRIP3` / `carStrip3()` in `index.html` |
| shipped | `assets/cars3d/<id>.png` + `wheels.json` + `CREDITS.txt` (4.6 MB) |

`rebuild-zip.py` walks `assets/` and root files only, so `tools/` never ships.

## Constants you must not "clean up"

- **`STRIP3.dir = -1`** — which way the strip sweeps vs how the game measures yaw. **Do not re-derive
  this from first principles.** I argued my way to +1 twice and was wrong twice. Drive it and look.
  Wrong sign = fine on a straight, rotates BACKWARDS through corners, *and* live wheels refuse to sit
  in the arches. One fault, two symptoms that look unrelated.
- **`STRIP3.phase = 0`** — a whole-turn offset. It was briefly 0.5 to correct a nose-on bake; that was
  the wrong place, because which end is the nose varies per model and belongs in the baker's per-car
  flip flag. Fixing the baker without clearing this = two 180°s = backwards again.
- **`STRIP_YS = 1/cos(tilt)`** — the bake is orthographic at 36.3°, the engine is a pinhole. Height and
  forward offsets differ between them by exactly this. Without it the cell is squashed against
  everything the engine projects itself, and live wheels sit outside the baked arches.
- **Sub-frame rotation** — nearest frame, then rotate the cell by the residual yaw × `sin(tilt)`.
  48 frames is 7.5° a step and even 96 still visibly steps at 240mph; this gives continuous rotation
  for free. More frames is the wrong lever.

## Wheels are drawn LIVE, not baked

A baked wheel can never steer or spin. So the baker locates the hubs, measures them in half-lengths,
and **hides them**; the game draws all four through the real projection under the body strip, front
pair steering, all four rolling from an odometer (`θ = distance / radius`).

- Hide by **REGION, not by match** — a wheel is tyre+rim+hub+disc+caliper, and hiding only matched
  meshes leaves bare white rim discs floating where the tyre was.
- The geometric test is the authority, the material NAME is only a hint: the ZL1 names its wheel
  material `Car_rubber_wheel` and then uses that rubber on trim running the whole car.
- **Plausibility guard**: failing extraction is fine (wheels stay baked in, just don't spin).
  Extracting something WRONG ships giant discs silently. Real cars: r 0.12–0.17 of half-length.

## Baker traps, each of which cost real time

- **Rank paint by SURFACE AREA, never triangle count.** Bodywork is a few enormous panels; wheels and
  interiors carry the geometry. Count picked `Rims` (10,380 tris) over `Body_paint` (2,066).
- **Colour multiplies the base texture** — a black-textured shell cannot go green. `!` prefix = paint
  hard (drop the map). Used for TORO VERDE; deliberately not used on the police livery or the
  Challenger's stripes, so their artwork survives.
- **Repaint must handle material ARRAYS.** A `!Array.isArray(o.material)` guard made the repaint
  silently do nothing on most detailed models.
- **Some Sketchfab archives ship ZERO images.** The ZL1's has none, so all 23 materials default to
  WHITE and the artist's intent survives only in the NAMES. The baker infers colour from name when a
  material is untextured *and* still pure white. **If a swapped model looks bleached, check this
  before touching the paint code.**
- **Clip planes must follow camera distance** — these meshes range 0.6 to 191 units long; a fixed
  `far` of 200 baked two cars as completely empty frames.
- **Orient by most-elongated-footprint sweep**, not longest AABB axis — some meshes sit at arbitrary yaw.
- Refresh `matrixWorld` before measuring anything after a translate, and zero `pivot.rotation` first.
  Measuring through a stale matrix put every wheel hub out by the centring offset; the tell was
  asymmetric output (`v` not ±equal).

## Quantisation is what pays for resolution

`PIL Image.quantize(colors=256, method=FASTOCTREE)` → **~14% of the file**, measured mean channel error
3.6/255, **alpha bit-identical**. 448px cells quantised (4.6 MB) ship *smaller* than 224px cells raw
(6.5 MB). **Must be FASTOCTREE** — MEDIANCUT drops the transparent palette slot and puts every car on a
black rectangle.

## Sourcing meshes (Sketchfab)

Search and faceCount are **public** — use curl, it is CORS-blocked from the browser. Downloads need a
login: `sketchfab.com/i/models/<uid>/download` (cookie auth) returns a **presigned S3 URL** that curl
can then fetch. Must be run from a **sketchfab.com origin**, not the game's localhost.

## Licensing — this is an obligation, not a nicety

Every mesh is **CC Attribution**; ShareAlike and NonCommercial were deliberately excluded (SA would try
to pull the game under its terms). `assets/cars3d/CREDITS.txt` ships automatically and **must also go on
the itch page**. In-game names stay QMM's own — the CC licence covers the mesh, not a manufacturer's
trademarks. Match the *era* too: a 1970 Camaro is not a stand-in for a modern ZL1.

## Open

- **Build is 39.8 MB** against the ~35 MB itch-mobile ceiling (music 22.2, superseded top-down sprites
  6.7, cars3d 4.6). cars3d is not the problem. Decide before deploying.
- Night still uses the daylit bake — headlight cones and brake glow are live on top, but the body
  doesn't darken. A second night-lit strip per car is the obvious fix.
- Nothing here is committed or deployed.

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

## Still open

- **Landmarks**: `park`, `lake`, `gas`, `school` interiors are fairly plain in 3D —
  the stadium, pyramids, sphinx and Golden Gate got the most attention.
- **Night mode** in the 3D view has had far less eyes-on than day. Headlight cones
  exist in the flat renderer but were never ported.
- **Figure-8 / Cross-Country** tracks render their water, overpass and jump ramp, but
  haven't been driven end-to-end in chase view.
- The **flat renderer** still carries all the old top-down polish (flower checkpoints,
  turn-guide chevrons, wet reflection streaks) that has only partly been carried over.

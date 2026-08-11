# Quantum Motors — rig handoff

Last updated 2026-08-11 by the Windows rig (2nd leg). Both rigs pull this repo, so
this file is the handoff channel until a dedicated mailbox exists.

---

## Where the game is live

| store | state | build |
|---|---|---|
| **itch.io** | live | build **#1875145**, stamped `de78dbf`, 36.0 MB |
| **Game Jolt** | listing complete, **NOT published** | still holds the older 39.7 MB zip |

Game Jolt IDs: game `1091069`, package `1116669`, release `1507665` (version 24.9.0).
The page is finished — description, tags, CC BY credits, header, thumbnail, 5 screenshots,
All Ages. It is deliberately unpublished; that call is Rob's.

Verify a live itch build by the **artifact**, never the dashboard:

```
butler status quantum-melanin-media/quantum-motors:html
# then read the embed URL out of data-iframe on the game page, fetch that
# index.html, and grep for a marker you just changed
```

## What shipped recently

- `04fb0db` — boost meter is named **QUANTUM**. It was printing the version string
  `M24.9e` in 7 player-facing places. Lines 6 and 126 still say M24.9e; those really
  are the version.
- `04fb0db` — **camera default is BIRDS-EYE** (`camMode = 1`). The pseudo-3D CHASE
  renderer is still WIP and was what every first-time player landed in. It is now
  opt-in via `C` / the 🎥 button. A returning player's saved `qmCam3` still wins.
- `de78dbf` — dropped 3 orphaned root sprites, 39.7 → 36.0 MB.
- `6b84892` — corrected NOTES-3D-RENDERER.md (see the trap below).
- `530450b`, `9f40970` — `tools/encode-music.py`.

---

## OPEN: the music re-encode  ← the live task

Build is 36.0 MB against a ~35 MB itch-mobile ceiling. Music is **22.2 MB, 56% of the
build**, and is the only lever with real weight left. Decision made: **40 kbps**.

**Run this on the rig that has the masters:**

```bash
git pull
python tools/encode-music.py "<real path to masters>"          # dry run, writes nothing
python tools/encode-music.py "<real path to masters>" --write
git add assets/music && git commit -m "chore(audio): re-encode soundtrack at 40k from masters" && git push
```

The other rig then rebuilds, smoke-tests, deploys and verifies.

### The contract, if you'd rather write your own encoder

- **Output exactly these 22 names** into `assets/music/`, because the game builds
  `assets/music/<name>.mp3` and 404s silently on anything else:
  `menu`, `t01_supasilky`, `t02_i_refuse`, `t03_it_is_what_it_is`, `t04_scfl`,
  `t05_i_am_affirmation`, `t06_heat_rock_caravan`, `t07_slap_in_the_saddle`,
  `t08_slap_jazz_rodeo`, `t09_fly_supa_groovy`, `t10_light_as_a_feather`,
  `t11_truth_is_the_feather`, `t12_kind_hands`, `t13_my_heart_at_home`,
  `t14_balance_of_maat`, `t15_the_lion_rises`, `t16_battle_of_kirina`,
  `t17_nine_witches_of_mali`, `t18_buffalo_woman_rising`, `t19_crippled_prince`,
  `t20_nana_triban`, `t21_kurukan_fuga`
- **Format:** `-c:a libmp3lame -b:a 40k -ac 1 -ar 48000`
- **Source must be the masters.** The files in `assets/music/` are already 48 kbps
  mono; re-compressing those stacks a second lossy generation and sounds worse than
  one clean pass from the master.

### Traps that already cost time

- **There is no 44 kbps.** MP3 bitrates are a fixed ladder; LAME silently rounds 44
  down to 40. Encoding at 44 and 40 produces byte-identical files. The menu is
  48 → 40 → 32.
- **Never fuzzy-match master filenames without printing the pairing first.** The
  archive at `C:\Users\respe\Music\n-Track Studio\` has `supa cala.wav`,
  `supa2done.wav`, `supacala115.wav`, `SUUPACALI.wav` and `supademo1.wav` side by
  side. Shipping the wrong take under the right filename is worse than failing loudly.
  `encode-music.py` refuses ambiguous matches and has `--map TRACK=FILENAME` for pins.
- The 66 kbps AAC files in `bloodlines-noble-chess/public/music/` are **not masters**,
  and only cover 15 of the 22 tracks. Same soundtrack, different lossy copy, different
  names. Worth unifying both projects onto one canonical set when the masters are cut.

### ⚠ The masters exist in exactly ONE place

They are on the other rig only — not in any repo, not in OneDrive (checked). The game,
the notes and the tooling are all recoverable from git. **The masters are not.** Get a
copy off that machine.

---

## OPEN: Game Jolt build swap

Game Jolt still has the pre-cut 39.7 MB zip. Before publishing, upload
`qmm-racing-itch.zip` (36.0 MB) to the release's **Upload Browser Build** box — the
right-hand one, whose help text mentions `index.html` in the root folder. The left box
is Downloadable and produces a zip players must extract themselves; that mistake was
already made once.

Add the new build first, then remove the old one, so the release is never left with
zero builds. Both files are named `qmm-racing-itch.zip` — tell them apart by size,
36 MB vs 39 MB.

## OPEN: the chase renderer

Still WIP, now opt-in. See `NOTES-3D-RENDERER.md` from line 260 for the baked-turntable
pipeline and `tools/bake3d/`.

---

## The notes trap, corrected in 6b84892

`NOTES-3D-RENDERER.md` used to say 6.7 MB of `assets/` root sprites were "superseded
top-down sprites" and implied they were free to delete. **Only 2.78 MB was dead.**
`roof1..roof8.png` (2.2 MB) are pulled in at runtime by the `ROOF` array via a *built*
path — so a literal filename grep reports zero references for art drawn on every
roadside building, in what is now the default camera.

Before deleting any asset, grep for the dynamic builders, not the filename:
`assets/'+c.file`, `assets/'+n+'.png`, `assets/photo/car_'+c.id+'.png`,
`assets/turn/'+id+'.png`, `assets/cars3d/'+id+'.png`, `assets/music/'+t.f+'.mp3`,
`assets/world/'+n+'.jpg`.

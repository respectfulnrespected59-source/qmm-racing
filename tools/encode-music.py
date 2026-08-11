"""Encode the soundtrack from MASTERS to the shipping MP3s.

    python tools/encode-music.py <masters_dir>                  # dry run: show the mapping
    python tools/encode-music.py <masters_dir> --write          # encode into assets/music/
    python tools/encode-music.py <masters_dir> --write --bitrate 32k

Why this exists
---------------
The build sits at 36.0 MB against a ~35 MB itch-mobile ceiling, and music is
22.2 MB of it -- 56% of everything. Dropping 48k -> 40k takes music to ~18.6 MB
and the build to ~32.3 MB, which clears the ceiling with room to spare.

MP3 bitrates are a fixed ladder. There is no 44k: LAME silently rounds it to 40.
The whole menu is 48 -> 40 -> 32.

ALWAYS ENCODE FROM THE MASTERS. The files currently in assets/music/ are already
48 kbps mono; re-compressing those to 40 stacks a second lossy generation on top
of the first and is audibly worse than a single 40 kbps encode from the source.
The masters live on the other rig -- that is the whole reason this script takes a
directory instead of just transcoding in place.

Output format matches what ships today: mono, 48 kHz. The game builds its paths as
assets/music/<name>.mp3, so the 22 output names below are not negotiable.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "assets" / "music"

# Exactly what index.html asks for: the TRACKS table's `f` values, plus the menu loop.
EXPECTED = [
    "menu",
    "t01_supasilky", "t02_i_refuse", "t03_it_is_what_it_is", "t04_scfl",
    "t05_i_am_affirmation", "t06_heat_rock_caravan", "t07_slap_in_the_saddle",
    "t08_slap_jazz_rodeo", "t09_fly_supa_groovy", "t10_light_as_a_feather",
    "t11_truth_is_the_feather", "t12_kind_hands", "t13_my_heart_at_home",
    "t14_balance_of_maat", "t15_the_lion_rises", "t16_battle_of_kirina",
    "t17_nine_witches_of_mali", "t18_buffalo_woman_rising", "t19_crippled_prince",
    "t20_nana_triban", "t21_kurukan_fuga",
]

AUDIO_EXT = {".wav", ".flac", ".aiff", ".aif", ".mp3", ".m4a", ".ogg", ".opus"}


def norm(s: str) -> str:
    """Collapse to comparable letters+digits: 'Supa Silky (master).wav' -> 'supasilky'."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug_of(expected: str) -> str:
    """'t01_supasilky' -> 'supasilky'; 'menu' -> 'menu'."""
    return norm(re.sub(r"^t\d\d_", "", expected))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("masters", type=Path, help="directory holding the master audio files")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--bitrate", default="40k")
    ap.add_argument("--write", action="store_true", help="actually encode (default is a dry run)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="encode even if some tracks have no master (leaves the old file in place)")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        print("ffmpeg not on PATH", file=sys.stderr)
        return 1
    if not args.masters.is_dir():
        print(f"not a directory: {args.masters}", file=sys.stderr)
        return 1

    candidates = [p for p in args.masters.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXT]
    if not candidates:
        print(f"no audio files under {args.masters}", file=sys.stderr)
        return 1

    # Match on the normalised stem. Exact first, then unique substring -- an ambiguous
    # substring is reported rather than guessed, because silently shipping the wrong
    # song under the right filename is worse than failing here.
    mapping, unmatched, ambiguous = {}, [], {}
    for want in EXPECTED:
        slug = slug_of(want)
        exact = [p for p in candidates if norm(p.stem) == slug]
        if len(exact) == 1:
            mapping[want] = exact[0]
            continue
        loose = [p for p in candidates if slug and slug in norm(p.stem)]
        if len(loose) == 1:
            mapping[want] = loose[0]
        elif len(loose) > 1:
            ambiguous[want] = loose
        else:
            unmatched.append(want)

    print(f"masters dir : {args.masters}")
    print(f"candidates  : {len(candidates)} audio file(s)")
    print(f"matched     : {len(mapping)}/{len(EXPECTED)}")
    print(f"bitrate     : {args.bitrate} mono 48 kHz\n")
    for want in EXPECTED:
        src = mapping.get(want)
        print(f"  {want:<28} <- {src.name if src else '** NO MASTER FOUND **'}")

    if ambiguous:
        print("\nAMBIGUOUS -- more than one master matched, refusing to guess:")
        for want, opts in ambiguous.items():
            print(f"  {want}: {', '.join(o.name for o in opts)}")
    if unmatched:
        print("\nNO MASTER for: " + ", ".join(unmatched))

    if (unmatched or ambiguous) and not args.allow_partial:
        print("\nNothing written. Fix the names, or re-run with --allow-partial.")
        return 1
    if not args.write:
        print("\nDry run. Re-run with --write to encode.")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    total = 0
    for want, src in mapping.items():
        dst = args.out / f"{want}.mp3"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
               "-c:a", "libmp3lame", "-b:a", args.bitrate,
               "-ac", "1", "-ar", "48000", str(dst)]
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print(f"FAILED on {want}", file=sys.stderr)
            return 1
        size = dst.stat().st_size
        total += size
        print(f"  {want:<28} {size/1024:7.0f} KB")

    print(f"\nmusic total: {total/1024/1024:.2f} MB  (was 22.24 MB)")
    print("Now: python rebuild-zip.py  ->  smoke test  ->  python deploy-itch.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

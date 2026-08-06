"""Deploy this build to itch.io via butler.

    python deploy-itch.py            # push
    python deploy-itch.py --dry-run  # stage + report, push nothing

Why this exists: on 2026-08-05 a butler push from another rig silently replaced the
photoreal "believable cities" build, and it went unnoticed for weeks because nothing
tied a live build back to a commit. Every push here is stamped with the git SHA, so
`butler status quantum-melanin-media/quantum-motors` answers "what is actually live?"
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

TARGET = "quantum-melanin-media/quantum-motors:html"
ROOT_FILES = ("index.html", "README.md")
STAGE = ROOT / "_deploy_stage"
DRY = "--dry-run" in sys.argv


def sh(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


# ── provenance ────────────────────────────────────────────────────────────────────
sha = sh("git", "rev-parse", "--short", "HEAD") or "nogit"
dirty = bool(sh("git", "status", "--porcelain"))
ahead = sh("git", "rev-list", "--count", "origin/master..HEAD") or "0"

version = sha + ("-dirty" if dirty else "")
print(f"commit:   {sha}")
print(f"clean:    {not dirty}")
print(f"unpushed: {ahead} commit(s) ahead of origin/master")

# Shipping something that is not on origin is how a build becomes unreproducible.
# Warning rather than a hard stop, so a hotfix is still possible.
if dirty or ahead != "0":
    print("\n  WARNING: working tree is dirty and/or ahead of origin.")
    print("  The live build will not be reproducible from origin. Commit and push first.\n")

# ── stage exactly what the zip ships ─────────────────────────────────────────────
missing = [f for f in ROOT_FILES if not (ROOT / f).exists()]
if missing or not (ROOT / "assets").is_dir():
    raise SystemExit(f"Not a qmm-racing checkout: missing {', '.join(missing) or 'assets/'}")

if STAGE.exists():
    shutil.rmtree(STAGE)
STAGE.mkdir()
for name in ROOT_FILES:
    shutil.copy2(ROOT / name, STAGE / name)
shutil.copytree(ROOT / "assets", STAGE / "assets")

files = [f for f in STAGE.rglob("*") if f.is_file()]
mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
print(f"staged:   {len(files)} files, {mb:.1f} MB -> {STAGE.name}/")

if DRY:
    print("\ndry run - nothing pushed.")
    raise SystemExit(0)

# ── push ─────────────────────────────────────────────────────────────────────────
print(f"\npushing to {TARGET} as version {version} ...")
r = subprocess.run(["butler", "push", str(STAGE), TARGET, "--userversion", version])
if r.returncode != 0:
    raise SystemExit(f"butler push failed (exit {r.returncode})")

print("\n--- butler status ---")
subprocess.run(["butler", "status", TARGET.split(":")[0]])
print(
    "\nNOT DONE YET. butler only uploads the file.\n"
    "  1. itch.io/game/edit/4754881 -> confirm THIS upload is the one ticked\n"
    "     'This file will be played in the browser'.\n"
    "  2. Then VERIFY THE ARTIFACT, not the dashboard: open the game page, read the\n"
    "     embed URL out of the data-iframe attribute, fetch that index.html, and grep\n"
    "     it for a marker you just changed. A green push is not a live build."
)

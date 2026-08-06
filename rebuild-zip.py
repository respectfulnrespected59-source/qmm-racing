"""Rebuild the itch.io / CrazyGames upload zip.

Run from anywhere:  python rebuild-zip.py
"""
import os
import zipfile
from pathlib import Path

# Anchored to THIS FILE's directory rather than a hardcoded absolute path. The
# previous version chdir'd to C:\\Users\\respe\\qmm-racing, which is not where the
# checkout lives on every rig, so it died on any machine but the one that wrote it.
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

ZIP_NAME = "qmm-racing-itch.zip"
ROOT_FILES = ("index.html", "README.md")

missing = [f for f in ROOT_FILES if not Path(f).exists()]
if missing or not Path("assets").is_dir():
    raise SystemExit(
        f"Not a qmm-racing checkout: {ROOT}\n"
        f"missing: {', '.join(missing) or 'assets/'}"
    )

if Path(ZIP_NAME).exists():
    os.remove(ZIP_NAME)

with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ROOT_FILES:
        z.write(name, name)
    for root, _dirs, files in os.walk("assets"):
        for f in files:
            fp = os.path.join(root, f)
            z.write(fp, fp.replace(os.sep, "/"))

print("rebuilt:", ROOT / ZIP_NAME)

with zipfile.ZipFile(ZIP_NAME) as z:
    names = z.namelist()
    size_mb = Path(ZIP_NAME).stat().st_size / (1024 * 1024)
    print("total entries:", len(names))
    print("index at root:", "index.html" in names)
    # itch's browser player chokes on backslash separators, so this must stay 0
    print("backslash entries:", len([n for n in names if "\\" in n]))
    print(f"zip size: {size_mb:.1f} MB")
    if size_mb > 100:
        print("WARNING: over itch's 100 MB cap for browser builds")

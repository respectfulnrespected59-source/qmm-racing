"""Decode a bake dump into assets/cars3d/ and palette-quantise it.

Second half of the offline bake pipeline (bake.html is the first). The browser hands back one line per car:

    <id>\t<meta json>\t<data:image/png;base64,...>

...which this writes out as assets/cars3d/<id>.png plus a merged wheels.json.

QUANTISATION IS THE WHOLE REASON THIS IS WORTH A SCRIPT. These are flat-shaded renders of low-poly cars: a few
hundred distinct colours across the entire strip. A 256-colour palette is visually lossless on that material
(measured: mean channel error 3.6/255, alpha bit-identical) and costs ~85% of the file. That saving is what pays
for the resolution -- 384px cells quantised ship SMALLER than the 224px cells did raw.

Alpha survives because FASTOCTREE reserves a palette slot for fully transparent pixels. MEDIANCUT does not, and
would flatten every car onto a black rectangle, so do not "simplify" the method argument.

Usage:  python tools/bake3d/install_strips.py <dumpfile> [<dumpfile> ...]
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "assets" / "cars3d"
COLORS = 256


def install(dump: Path) -> list[tuple[str, int, int]]:
    raw = dump.read_text(encoding="utf-8")
    payload = json.loads(raw) if raw.lstrip().startswith('"') else raw
    if payload.startswith(("ERROR", "PENDING")):
        raise SystemExit(f"{dump.name}: bake did not finish -> {payload[:300]}")

    wheels_path = OUT / "wheels.json"
    wheels = json.loads(wheels_path.read_text()) if wheels_path.exists() else {}
    results: list[tuple[str, int, int]] = []

    for line in payload.split("\n"):
        if not line.strip():
            continue
        car_id, meta_json, data_url = line.split("\t", 2)
        meta = json.loads(meta_json)
        png = base64.b64decode(data_url.split(",", 1)[1])

        target = OUT / f"{car_id}.png"
        target.write_bytes(png)
        before = len(png)

        img = Image.open(target).convert("RGBA")
        img.quantize(colors=COLORS, method=Image.FASTOCTREE).save(target, optimize=True)
        after = target.stat().st_size

        wheels[car_id] = meta["wheels"]
        results.append((car_id, before, after))

    wheels_path.write_text(json.dumps(wheels, separators=(",", ":")))
    return results


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    OUT.mkdir(parents=True, exist_ok=True)
    total_before = total_after = 0
    for arg in sys.argv[1:]:
        for car_id, before, after in install(Path(arg)):
            total_before += before
            total_after += after
            print(f"  {car_id:<11} {before/1024:6.0f} KB -> {after/1024:5.0f} KB  ({100*after/before:.0f}%)")
    print(f"\ntotal {total_before/1048576:.1f} MB -> {total_after/1048576:.1f} MB")
    strips = sorted(OUT.glob("*.png"))
    print(f"{len(strips)} strips, {sum(p.stat().st_size for p in strips)/1048576:.1f} MB on disk")


if __name__ == "__main__":
    main()

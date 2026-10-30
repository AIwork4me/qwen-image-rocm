"""Contact-sheet grid from a benchmark run's measured outputs.

Usage: python -I bench/make_contact_sheet.py <raw_dir> <out_png>

<raw_dir> is results/raw/<date>; measured images are the -r<idx>.png files
(warmup uses seed[0] without -r suffix; cold.png excluded). Tiles carry a
small filename label. Output is a 3-per-row grid of 256px tiles.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw


def collect(raw_dir: Path) -> list[Path]:
    pngs = []
    for sub in sorted(raw_dir.rglob("*")):
        if sub.is_file() and sub.suffix == ".png":
            stem = sub.stem
            if any(part.startswith("r") and part[1:].isdigit() for part in stem.split("-")):
                pngs.append(sub)
    return sorted(pngs)


def make_sheet(raw_dir: str, out_png: str, tile: int = 256) -> int:
    files = collect(Path(raw_dir))
    if not files:
        raise SystemExit(f"no measured images under {raw_dir}")
    cols = 3
    rows = (len(files) + cols - 1) // cols
    label_h = 18
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        img = Image.open(f).convert("RGB").resize((tile, tile))
        x, y = (i % cols) * tile, (i // cols) * (tile + label_h)
        sheet.paste(img, (x, y))
        draw.text((x + 2, y + tile + 2), f.parent.parent.name + "/" + f.name, fill="black")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return len(files)


if __name__ == "__main__":
    n = make_sheet(sys.argv[1], sys.argv[2])
    print(f"contact sheet with {n} tiles -> {sys.argv[2]}")

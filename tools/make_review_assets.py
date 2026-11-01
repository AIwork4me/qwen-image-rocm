"""Owner-review convenience assets for issue #5 (viewing aids only).

The evidence files stay untouched; everything here is a DERIVED VIEW of the
committed PNGs, sized for GitHub inline rendering (<5 MB, camo-friendly):
- per-prompt row strips of the r1 quality grid (zoomable per prompt)
- a downscaled JPEG preview of the 2048 typography sample (5.34 MB original
  does not render inline in issues)
Run: phase3-quality/.venv/Scripts/python.exe -I tools/make_review_assets.py
"""

import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
GRID = REPO / "bench" / "results" / "2026-11-01-r1-triple" / "quality_grid.png"
P2048 = REPO / "docs" / "gallery" / "fast-2048-p3-poster-seed42.png"
OUT = REPO / "docs" / "release-audit" / "review-assets"

PROMPTS = ["p1-zh-scene", "p2-en-scene", "p3-poster-text"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    grid = Image.open(GRID)
    w, h = grid.size          # 1536 x 828: 3 labeled rows of [base|exp] x 3 seeds
    row_h = h // 3
    for i, prompt in enumerate(PROMPTS):
        strip = grid.crop((0, i * row_h, w, min((i + 1) * row_h, h)))
        dest = OUT / f"r1-grid-row{i + 1}-{prompt}.png"
        strip.save(dest, optimize=True)
        print(f"{dest.name}: {dest.stat().st_size / 1e6:.2f} MB")
    # 2048 poster preview: half-size JPEG, clearly labeled as a view
    im = Image.open(P2048).convert("RGB")
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    dest = OUT / "p3-poster-2048-preview-half.jpg"
    im.save(dest, quality=88, optimize=True)
    print(f"{dest.name}: {dest.stat().st_size / 1e6:.2f} MB")
    (OUT / "PROVENANCE.md").write_text(
        "# Review-assets provenance\n\n"
        "These files are VIEWING AIDS derived from committed evidence for\n"
        "issue #5 inline display — not new evidence, not retouched:\n\n"
        "- `r1-grid-row{1,2,3}-<prompt>.png` — exact row crops of\n"
        "  `bench/results/2026-11-01-r1-triple/quality_grid.png`\n"
        "  (rows: prompts; columns: seeds r0/r1/r2; each cell left = E8\n"
        "  baseline, right = production triple).\n"
        "- `p3-poster-2048-preview-half.jpg` — 50% LANCZOS downscale of\n"
        "  `docs/gallery/fast-2048-p3-poster-seed42.png` (5.34 MB original\n"
        "  exceeds GitHub inline-render size; view/download the original for\n"
        "  full glyph detail).\n\n"
        "Generator: `tools/make_review_assets.py` (deterministic).\n",
        encoding="utf-8",
    )
    print("PROVENANCE.md written")


if __name__ == "__main__":
    sys.exit(main())

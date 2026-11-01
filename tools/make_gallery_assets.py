"""Build docs/gallery/ + assets/social-preview.png from REAL run outputs.

Every gallery image is copied from a schema-validated run record's raw
output (see docs/gallery/PROVENANCE.md, generated alongside). The social
preview composes the same real images — no stock/synthetic art anywhere.
Run: phase3-quality/.venv/Scripts/python.exe -I tools/make_gallery_assets.py
"""

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
GALLERY = REPO / "docs" / "gallery"
ASSETS = REPO / "assets"

# (source, dest, caption-provenance)
COPIES = [
    (RAW / "2026-11-01-r1-triple/p1-zh-scene-42-r0.png",
     "fast-1024-p1-zh-scene-seed42.png",
     "Fast profile (turbo int8 DiT + int8 TE + ck + nosmart), 1024², 8 steps, seed 42, p1-zh-scene — run 2026-11-01-r1-triple (r0 measure)"),
    (RAW / "2026-11-01-r1-triple/p2-en-scene-42-r0.png",
     "fast-1024-p2-en-scene-seed42.png",
     "Fast profile, 1024², 8 steps, seed 42, p2-en-scene — run 2026-11-01-r1-triple (r0 measure)"),
    (RAW / "2026-11-01-r1-triple/p3-poster-text-42-r0.png",
     "fast-1024-p3-poster-seed42.png",
     "Fast profile, 1024², 8 steps, seed 42, p3-poster-text (Chinese typography) — run 2026-11-01-r1-triple (r0 measure)"),
    (RAW / "2026-11-01-r2-2048fast/p2-en-scene-42-r0.png",
     "fast-2048-p2-en-scene-seed42.png",
     "Fast profile, 2048² native, 8 steps, seed 42, p2-en-scene — run 2026-11-01-r2-2048fast (r0 measure)"),
]

PREVIEW_TILES = ["fast-1024-p1-zh-scene-seed42.png", "fast-1024-p3-poster-seed42.png",
                 "fast-2048-p2-en-scene-seed42.png", "fast-1024-p2-en-scene-seed42.png"]


def font(size: int, bold: bool = True, cjk: bool = False) -> ImageFont.FreeTypeFont:
    if cjk:
        for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf"):
            p = Path("C:/Windows/Fonts") / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    for name in ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"):
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def make_gallery() -> None:
    GALLERY.mkdir(parents=True, exist_ok=True)
    lines = ["# Gallery provenance\n",
             "Every image is an unedited output of a recorded, schema-validated run",
             "(records: `bench/results/<run>/`, protocol: `bench/prompts.json`).",
             "Do not crop/recolor these files — they are evidence.\n"]
    for src, dest, caption in COPIES:
        if not src.exists():
            sys.exit(f"missing source {src} — run the r1/r2 measurements first")
        shutil.copy2(src, GALLERY / dest)
        lines.append(f"- `{dest}` — {caption}")
        print(f"gallery: {dest}")
    (GALLERY / "PROVENANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tile(img: Image.Image, w: int, h: int) -> Image.Image:
    s = min(w / img.width, h / img.height)
    im = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    out = Image.new("RGB", (w, h), (10, 14, 26))
    out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


def make_preview() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    W, H = 1280, 640
    canvas = Image.new("RGB", (W, H), (10, 14, 26))
    d = ImageDraw.Draw(canvas)
    # right: 2x2 real-output tiles
    gap, tw, th = 16, 300, 280
    x0 = W - 2 * tw - gap - 24
    for i, name in enumerate(PREVIEW_TILES):
        t = tile(Image.open(GALLERY / name), tw, th)
        canvas.paste(t, (x0 + (i % 2) * (tw + gap), 36 + (i // 2) * (th + gap)))
        d.rectangle([x0 + (i % 2) * (tw + gap), 36 + (i // 2) * (th + gap),
                     x0 + (i % 2) * (tw + gap) + tw, 36 + (i // 2) * (th + gap) + th],
                    outline=(90, 160, 255), width=2)
    # left: text block
    f1 = font(52); f2 = font(30); f3 = font(24, bold=False)
    d.text((44, 70), "Qwen-Image 2.1", font=f1, fill=(240, 244, 255))
    d.text((44, 140), "on AMD Radeon GPUs", font=f1, fill=(90, 200, 250))
    d.text((44, 236), "Native Windows ROCm  ·  RX 7900 XTX 24 GB", font=f2, fill=(200, 210, 230))
    d.text((44, 292), "1024²: ~8 s/image warm (measured)", font=f3, fill=(160, 255, 180))
    d.text((44, 330), "2048² native generation unlocked", font=f3, fill=(160, 255, 180))
    d.text((44, 368), "Reproducible benchmarks + quickstart", font=f3, fill=(160, 255, 180))
    d.text((44, 440), "github.com/AIwork4me/qwen-image-rocm", font=font(26), fill=(120, 140, 180))
    d.text((44, 500), "开源 · 可复现 · 真实测量 (open-source, reproducible, measured)",
           font=font(22, bold=False, cjk=True), fill=(150, 160, 190))
    out = ASSETS / "social-preview.png"
    canvas.save(out, optimize=True)
    print(f"preview: {out} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    make_gallery()
    make_preview()

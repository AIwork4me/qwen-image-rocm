r"""Quality-gate tooling (design doc 画质门槛协议): paired grids + LPIPS.

Each speed experiment pairs against the bf16-40-step baseline at the same
prompt+seed. Deliberately TWO separate outputs:

1. quality_grid.png — side-by-side [baseline | experiment] tiles per prompt
   and seed (256 px) for the overall look.
2. quality_crops_poster.png — NATIVE-resolution 512² crops of the poster
   prompt (Qwen's text rendering is the project's own acceptance axis; a
   256 px downscale cannot show text degradation).

LPIPS(alex) semantics MUST be declared per experiment (review finding):
- fidelity : same-model numerics variants (quant / attention backends).
             Same-seed divergence measures reference drift.
- distance : different model or schedule (Turbo 8-step). LPIPS is a
             perceptual DISTANCE, not a quality score — a visually fine
             Turbo image can score high. The three-tier verdict
             (无感 / 略降 / 不可接受) stays a human call on the grids.

Run inside the phase3-quality venv (PyPI CPU torch + lpips + pillow + numpy):

  ..\phase3-quality\.venv\Scripts\python.exe -I bench\quality_gate.py ^
      --baseline results\raw\<date-baseline> --experiment results\raw\<date-exp> ^
      --experiment-name p3-turbo-8step --semantics distance ^
      --out bench\results\<date-exp> [--noise-a a.png --noise-b b.png]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]

_lpips_model = None


def _lpips_pair_impl(a: Path, b: Path) -> float:
    global _lpips_model
    import numpy as np
    import torch

    if _lpips_model is None:
        import lpips

        _lpips_model = lpips.LPIPS(net="alex")  # weights pre-fetched to torch hub cache
    a_t = torch.from_numpy(np.asarray(Image.open(a).convert("RGB"), dtype=np.float32))
    b_t = torch.from_numpy(np.asarray(Image.open(b).convert("RGB"), dtype=np.float32))
    a_t = (a_t / 127.5 - 1.0).permute(2, 0, 1)[None]
    b_t = (b_t / 127.5 - 1.0).permute(2, 0, 1)[None]
    with torch.no_grad():
        return float(_lpips_model(a_t, b_t).item())


def collect_measured(raw_dir: str | Path) -> dict[tuple[str, int], Path]:
    """Map (prompt_id, run_idx) -> png for measured runs (-r<idx>.png files)."""
    out: dict[tuple[str, int], Path] = {}
    for f in sorted(Path(raw_dir).glob("*.png")):
        parts = f.stem.split("-")
        if len(parts) >= 3 and parts[-1].startswith("r") and parts[-1][1:].isdigit():
            out[("-".join(parts[:-2]), int(parts[-1][1:]))] = f
    return out


def make_paired_grid(
    base: dict[tuple[str, int], Path],
    exp: dict[tuple[str, int], Path],
    out_png: str | Path,
    tile: int = 256,
) -> int:
    """Rows = prompts, columns = [base|exp] per seed (run_idx), labeled."""
    pairs = sorted(k for k in base.keys() & exp.keys())
    if not pairs:
        raise SystemExit("no (prompt, run_idx) pairs between baseline and experiment")
    prompts = sorted({p for p, _ in pairs})
    idxs = sorted({i for _, i in pairs})
    label_h = 20
    cols = len(idxs) * 2
    rows = len(prompts)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, prompt in enumerate(prompts):
        for c, idx in enumerate(idxs):
            for j, (which, m) in enumerate((("base", base), ("exp", exp))):
                f = m.get((prompt, idx))
                if f is None:
                    continue
                img = Image.open(f).convert("RGB").resize((tile, tile))
                x = (c * 2 + j) * tile
                y = r * (tile + label_h)
                sheet.paste(img, (x, y))
                draw.text(
                    (x + 2, y + tile + 2),
                    f"{prompt} r{idx} {which}",
                    fill="black",
                )
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return len(pairs)


def make_native_crops(
    base_png: Path,
    exp_png: Path,
    out_png: str | Path,
    crop: int = 512,
) -> None:
    """Two native-res 512² crops (upper-center / lower-center) of one pair.

    The poster prompt's acceptance criterion is text sharpness; downscaled
    tiles hide exactly that. Crops are pasted at 1:1 scale.
    """
    regions = ((256, 64), (256, 560))
    label_h = 20
    sheet = Image.new("RGB", (2 * crop, 2 * (crop + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, (which, f) in enumerate((("baseline", base_png), ("experiment", exp_png))):
        img = Image.open(f).convert("RGB")
        for c, (x0, y0) in enumerate(regions):
            tile = img.crop((x0, y0, x0 + crop, y0 + crop))
            x, y = c * crop, r * (crop + label_h)
            sheet.paste(tile, (x, y))
            draw.text((x + 2, y + crop + 2), f"{which} crop@({x0},{y0})", fill="black")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)


def lpips_table(
    base: dict[tuple[str, int], Path],
    exp: dict[tuple[str, int], Path],
) -> dict[str, dict]:
    """Per-prompt LPIPS stats (medians per prompt — never pool across prompts:
    poster distance and scene distance are different distributions)."""
    table: dict[str, dict] = {}
    for (prompt, idx) in sorted(base.keys() & exp.keys()):
        score = _lpips_pair_impl(base[(prompt, idx)], exp[(prompt, idx)])
        stats = table.setdefault(prompt, {"scores": []})
        stats["scores"].append(score)
    for prompt, stats in table.items():
        scores = stats["scores"]
        stats["median"] = statistics.median(scores)
        stats["max"] = max(scores)
        stats["n"] = len(scores)
    return table


SEMANTICS_NOTE = {
    "fidelity": (
        "LPIPS semantics: FIDELITY — same model, same seed, only the numerics "
        "path changed (quantization / attention backend). Lower = closer to the "
        "bf16 reference; compare against the noise floor before reading "
        "anything into small values."
    ),
    "distance": (
        "LPIPS semantics: DISTANCE, NOT QUALITY — a different model/schedule "
        "(Turbo) legitimately produces different images; a high score does not "
        "mean worse. The three-tier verdict is the user's 目检 call on the grid."
    ),
}


def describe_baseline(baseline_dir: str | Path, override: str | None = None) -> str:
    """Human description of what the baseline images actually are.

    Derived from the baseline's own run records (raw dirs are named after
    their bench/results/<name>/ records dir), never hardcoded — a fidelity
    gate against e8 (turbo int8, 8 steps) must not be labeled "bf16, 40
    steps" (regression: r1-triple's quality.md shipped with exactly that
    wrong label). ``override`` wins; no records found -> explicit "(no run
    records found...)" so a mislabel cannot slip through silently.
    """
    if override:
        return override
    name = Path(baseline_dir).name
    records = REPO / "bench" / "results" / name
    jsons = sorted(records.glob("*.json")) if records.is_dir() else []
    if not jsons:
        return f"`{baseline_dir}` (no run records found for {name!r} — pass --baseline-desc)"
    r = json.loads(jsons[0].read_text(encoding="utf-8"))
    bits = [str(r.get("precision", "?")), f"{r.get('steps', '?')} steps"]
    unet, clip = r.get("unet"), r.get("clip")
    if unet:
        bits.append(unet.replace(".safetensors", ""))
    if clip:
        bits.append("TE " + clip.replace(".safetensors", "").replace("qwen3vl_8b_", ""))
    return f"`{baseline_dir}` ({r.get('experiment', name)}: " + ", ".join(bits) + ")"


def write_quality_md(
    out_md: Path,
    experiment_name: str,
    semantics: str,
    table: dict[str, dict],
    noise_floor: float | None,
    baseline_dir: str,
    experiment_dir: str,
    baseline_desc: str | None = None,
) -> None:
    lines = [
        f"# Quality gate — {experiment_name}",
        "",
        f"- Baseline: {describe_baseline(baseline_dir, baseline_desc)}",
        f"- Experiment: `{experiment_dir}`",
        f"- {SEMANTICS_NOTE[semantics]}",
    ]
    if noise_floor is not None:
        lines.append(
            f"- LPIPS noise floor (same-config determinism): **{noise_floor:.4f}** "
            "— differences below this are noise."
        )
    lines += [
        "",
        "| Prompt | median LPIPS | max LPIPS | n pairs |",
        "|---|---|---|---|",
    ]
    for prompt, s in sorted(table.items()):
        lines.append(f"| {prompt} | {s['median']:.4f} | {s['max']:.4f} | {s['n']} |")
    lines += [
        "",
        "## Verdict (user final — 三档终审)",
        "",
        "- [ ] 无感 (imperceptible)",
        "- [ ] 略降 (slightly degraded)",
        "- [ ] 不可接受 (unacceptable)",
        "",
        "Notes: ",
        "",
        "Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` "
        "(native-res text crops, poster prompt).",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True, help="raw dir of the bf16 baseline runs")
    ap.add_argument("--experiment", required=True, help="raw dir of the experiment runs")
    ap.add_argument("--experiment-name", required=True)
    ap.add_argument("--semantics", choices=["fidelity", "distance"], required=True)
    ap.add_argument("--out", required=True, help="results dir for quality.md + grids")
    ap.add_argument("--poster-prompt", default="p3-poster-text")
    ap.add_argument("--noise-a", default=None, help="same-config rerun image A")
    ap.add_argument("--noise-b", default=None, help="same-config rerun image B")
    ap.add_argument("--skip-lpips", action="store_true",
                    help="grids only (torch/lpips unavailable)")
    ap.add_argument("--baseline-desc", default=None,
                    help="explicit baseline description (default: derived from the"
                         " baseline's own run records; required if none exist)")
    ns = ap.parse_args(sys.argv[1:])

    out_dir = Path(ns.out)
    base = collect_measured(ns.baseline)
    exp = collect_measured(ns.experiment)

    n = make_paired_grid(base, exp, out_dir / "quality_grid.png")
    print(f"paired grid: {n} pairs -> {out_dir / 'quality_grid.png'}")

    b0, e0 = base.get((ns.poster_prompt, 0)), exp.get((ns.poster_prompt, 0))
    if b0 and e0:
        make_native_crops(b0, e0, out_dir / "quality_crops_poster.png")
        print(f"native-res poster crops -> {out_dir / 'quality_crops_poster.png'}")

    noise_floor = None
    table: dict[str, dict] = {}
    if not ns.skip_lpips:
        table = lpips_table(base, exp)
        if ns.noise_a and ns.noise_b:
            noise_floor = _lpips_pair_impl(Path(ns.noise_a), Path(ns.noise_b))
            print(f"LPIPS noise floor: {noise_floor:.4f}")
        for prompt, s in sorted(table.items()):
            print(f"LPIPS {prompt}: median={s['median']:.4f} max={s['max']:.4f} n={s['n']}")
    else:
        print("LPIPS skipped (--skip-lpips)")

    write_quality_md(
        out_dir / "quality.md", ns.experiment_name, ns.semantics, table,
        noise_floor, ns.baseline, ns.experiment, baseline_desc=ns.baseline_desc,
    )
    print(f"quality.md -> {out_dir / 'quality.md'}")

    # machine-readable echo: the doc/transcription layer (READMEs, matrices,
    # release notes) reads THIS, so per-prompt numbers cannot transpose again
    base_records = REPO / "bench" / "results" / Path(ns.baseline).name
    base_jsons = sorted(base_records.glob("*.json")) if base_records.is_dir() else []
    base_experiment = (
        json.loads(base_jsons[0].read_text(encoding="utf-8"))["experiment"]
        if base_jsons else None
    )
    echo = {
        "experiment_name": ns.experiment_name,
        "semantics": ns.semantics,
        "baseline_dir": ns.baseline,
        "baseline_experiment": base_experiment,
        "baseline_desc": describe_baseline(ns.baseline, ns.baseline_desc),
        "median": {p: s["median"] for p, s in table.items()},
        "max": {p: s["max"] for p, s in table.items()},
        "n_pairs": {p: s["n"] for p, s in table.items()},
        "noise_floor": noise_floor,
        "monitor": "lpips(alex, v0.1)",
    }
    (out_dir / "quality.json").write_text(
        json.dumps(echo, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"quality.json -> {out_dir / 'quality.json'}")


if __name__ == "__main__":
    main()

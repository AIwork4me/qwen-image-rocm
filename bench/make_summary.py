"""Phase 3 cross-experiment summary (protocol v1.3).

Aggregates every experiment dir under bench/results/ (measure runs only),
computes per-prompt medians and same-session paired ratios vs the shadow
control (p3-control-bf16), and emits a Markdown table. LPIPS columns are
transcribed from each experiment's quality.md (semantic-split, per-prompt).

Usage: uv run --python 3.12 --with jsonschema --with matplotlib python -I \
       bench/make_summary.py <control_date_dir> <out_md> [more date dirs...]
"""

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

LABELS = {
    "p3-control-bf16-1024x1024": "bf16 control (shadow)",
    "p3-turbo-8step-1024x1024": "Turbo 8-step bf16",
    "p3-turbo-int8-1024x1024": "Turbo 8-step int8",
    "p3-int8-dit-1024x1024": "int8 DiT (40-step)",
    "p3-int8-te-1024x1024": "int8 TE (40-step)",
    "p3-w4a8-te-1024x1024": "w4a8 TE (40-step)",
    "p3-int8-dit-te-1024x1024": "int8 DiT+TE (40-step)",
    "p3-vaetiled-1024x1024": "VAE tiled (40-step)",
    "p3-attn-nomath-1024x1024": "attn: default, no wrapper",
    "p3-attn-split-1024x1024": "attn: split",
    "p3-attn-quad-1024x1024": "attn: quad (sub-quadratic)",
    "p3-attn-ck-1024x1024": "attn: ck",
    "p3-attn-pytorch-math-1024x1024": "attn: pytorch+math-hard",
    "p3-attn-pytorch-aotriton-1024x1024": "attn: pytorch+aotriton",
    "p3-vram-highvram-1024x1024": "vram: --highvram",
    "p3-vram-nosmart-1024x1024": "vram: --disable-smart-memory",
    "p3-vram-cache-none-1024x1024": "vram: --cache-none",
    "p3-vram-fp16acc-1024x1024": "vram: --fast fp16_accumulation",
    "p2-comfyui-1024x1024": "p2 baseline (historical)",
}


def medians(date_dir: Path) -> dict:
    out: dict[str, dict] = {}
    for f in sorted(date_dir.glob("*-r*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("run_kind") != "measure":
            continue
        cell = out.setdefault(
            rec["experiment"],
            {"totals": {}, "vram_peak": 0.0, "steps": rec["steps"], "n": 0},
        )
        cell["totals"].setdefault(rec["prompt_id"], []).append(rec["runs"][0]["total_s"])
        cell["vram_peak"] = max(cell["vram_peak"], rec["vram_peak_mb"] or 0)
        cell["n"] += 1
    for cell in out.values():
        cell["medians"] = {p: statistics.median(v) for p, v in cell["totals"].items()}
    return out


def main() -> None:
    control_dir = Path(sys.argv[1])
    out_md = Path(sys.argv[2])
    dirs = [Path(d) for d in sys.argv[3:]] or sorted(
        (REPO / "bench" / "results").glob("2026-*e[1247]*"),
    )
    ctrl = medians(control_dir)
    ctrl_exps = list(ctrl)
    if len(ctrl_exps) != 1:
        raise SystemExit(f"control dir must hold exactly one experiment, got {ctrl_exps}")
    ctrl_med = ctrl[ctrl_exps[0]]["medians"]

    rows = {}
    for d in dirs:
        for exp, cell in medians(d).items():
            rows[exp] = cell

    lines = [
        "# Phase 3 cross-experiment summary (protocol v1.3)",
        "",
        f"Generated {datetime.now().isoformat(timespec='seconds')}. "
        "All numbers = median of measured runs; ratios are same-session "
        "paired vs the bf16 shadow control "
        f"(`{ctrl_exps[0]}`, dir `{control_dir.name}`).",
        "",
        "| Experiment | steps | p1 med (s) | p2 med (s) | p3 med (s) | "
        "speedup p1/p2/p3 | VRAM peak (MB) | n |",
        "|---|---|---|---|---|---|---|---|",
    ]
    order = sorted(rows, key=lambda e: min(rows[e]["medians"].values()))
    for exp in order:
        cell = rows[exp]
        m = cell["medians"]
        p1, p2, p3 = m.get("p1-zh-scene"), m.get("p2-en-scene"), m.get("p3-poster-text")
        if None in (p1, p2, p3):
            continue  # incomplete experiment (probe/partial)
        ratio = " / ".join(
            f"{ctrl_med[p] / v:.2f}x" for p, v in (
                ("p1-zh-scene", p1), ("p2-en-scene", p2), ("p3-poster-text", p3))
        )
        label = LABELS.get(exp, exp)
        lines.append(
            f"| {label} | {cell['steps']} | {p1:.1f} | {p2:.1f} | {p3:.1f} "
            f"| {ratio} | {cell['vram_peak']:.0f} | {cell['n']} |"
        )
    lines += [
        "",
        "Notes: turbo-int8 2048² probe (not in table): 42.2s steady at native "
        "resolution; int8-dit-te 2048² probe: 328s (40-step). "
        "LPIPS verdict tables: per-experiment quality.md.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

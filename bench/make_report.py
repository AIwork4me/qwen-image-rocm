"""Markdown report + plots from a bench/results/<date>/ directory.

Reads every run JSON (schema bench/schema/result.schema.json), validates it,
groups measured runs by (experiment, prompt_id), and writes report.md with
medians, min/max, run counts, protocol version, and a Limitations section.
Plots use the Agg backend (no display needed).
"""

import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((REPO / "bench" / "schema" / "result.schema.json").read_text())


def _load_runs(results_dir: str):
    from jsonschema import validate

    rdir = Path(results_dir)
    records = []
    for f in sorted(rdir.rglob("*.json")):
        if f.name == "report.md":
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        validate(rec, SCHEMA)
        records.append(rec)
    return records


def make_report(results_dir: str) -> None:
    rdir = Path(results_dir)
    records = _load_runs(results_dir)
    # measured runs are tagged "run_kind": "measure" by run_bench (schema allows
    # extra properties); warmup runs share seed[0] and must not enter medians.
    measured = [r for r in records if r.get("run_kind") == "measure"]

    groups: dict[tuple, list] = {}
    for r in measured:
        groups.setdefault((r["experiment"], r["prompt_id"]), []).append(r)

    lines = [
        "# Phase 1 diffusers baseline report",
        "",
        f"- Protocol: `{records[0]['protocol_version'] if records else 'n/a'}`"
        if records else "# report",
        f"- Runs per config: median of {max(len(v) for v in groups.values()) if groups else 0}"
        if groups else "",
        f"- Environment: `{records[0]['env_ref'] if records else 'n/a'}`",
        "",
        "| Config | Prompt | median total (s) | min–max (s) | s/step | VRAM (MB) | n |",
        "|---|---|---|---|---|---|---|",
    ]
    rows = []
    for (experiment, prompt_id), rs in sorted(groups.items()):
        totals = [r["runs"][-1]["total_s"] for r in rs]
        spstep = [r["runs"][-1]["denoise_s"] / r["steps"] for r in rs]
        vram = max(r["vram_peak_mb"] for r in rs)
        med = statistics.median(totals)
        lines.append(
            f"| {experiment} | {prompt_id} | {med:.1f} | "
            f"{min(totals):.1f}–{max(totals):.1f} | "
            f"{statistics.median(spstep):.2f} | {vram:.0f} | {len(rs)} |"
        )
        rows.append((experiment, prompt_id, med))

    cold = [r for r in records if r["runs"][-1]["kind"] == "cold"]
    if cold:
        c = cold[0]
        lines += [
            "",
            f"Cold run (first load, {c['experiment']}, {c['prompt_id']}): "
            f"{c['runs'][-1]['total_s']}s total, denoise {c['runs'][-1]['denoise_s']}s.",
        ]

    lines += [
        "",
        "## Limitations",
        "",
        "- Single machine, single GPU (AMD Radeon RX 7900 XTX, Windows-native ROCm);",
        "  numbers are not comparable across machines or driver versions.",
        "- Text-encode and VAE-decode stages are not separately timed in this phase;",
        "  `denoise_s` covers the denoising loop only (see run_bench.py header).",
        "- Median of 3 measured runs per config; variance between runs is reported",
        "  as min–max, not confidence intervals.",
        "- No cross-framework claim: diffusers-only in this report.",
        "",
    ]
    (rdir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    if rows:
        labels = [f"{e}\n{p}" for e, p, _ in rows]
        meds = [m for _, _, m in rows]
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.bar(labels, meds)
        ax.set_ylabel("median total wall time (s)")
        ax.set_title("Speed by config (diffusers baseline, protocol v1)")
        plt.xticks(rotation=30, ha="right", fontsize=8)
        fig.tight_layout()
        fig.savefig(rdir / "speed_by_config.png", dpi=120)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(12, 5))
        for (experiment, prompt_id), rs in sorted(groups.items()):
            series = [r["runs"][-1]["step_times_s"] for r in rs]
            series = [s for s in series if s]
            if series:
                ax.plot(series[0], label=f"{experiment}/{prompt_id}", alpha=0.7)
        ax.set_xlabel("denoising step")
        ax.set_ylabel("step wall time (s)")
        ax.set_title("Per-step time (first measured run per config)")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(rdir / "step_time_breakdown.png", dpi=120)
        plt.close(fig)


if __name__ == "__main__":
    import sys

    make_report(sys.argv[1])

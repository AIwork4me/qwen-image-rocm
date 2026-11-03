"""Report aggregation for the Linux W7900 lab.

Reads all ``bench/results/linux-w7900/<run_id>/*.json`` records, computes
per-experiment warm/fresh/cold latency + memory statistics, and writes
``bench/results/linux-w7900/SUMMARY.json`` + ``SUMMARY.md``. Charts are
generated only from these aggregated raw measurements.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from . import lab_env


def _load_records() -> list[dict]:
    records = []
    root = lab_env.RESULTS_ROOT
    if not root.is_dir():
        return records
    for run_dir in sorted(root.iterdir()):
        if not run_dir.is_dir() or run_dir.name in ("raw", "env"):
            continue
        for f in sorted(run_dir.glob("*.json")):
            if f.name.startswith("server"):
                continue
            try:
                records.append(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    return records


def summarize_experiment(records: list[dict]) -> dict:
    exp = records[0]["experiment"]
    warm = [r for r in records if r["run_kind"] == "measure"]
    fresh = [r for r in records if r["run_kind"] == "fresh_prompt"]
    cold = [r for r in records if r["run_kind"] == "cold"]

    def med(rs, key):
        vals = [r["runs"][0][key] for r in rs if r["runs"][0].get(key) is not None]
        return round(statistics.median(vals), 3) if vals else None

    def mx(rs, key):
        vals = [r.get(key) for r in rs if r.get(key) is not None]
        return round(max(vals), 1) if vals else None

    steps = [r.get("steady_step_median_s") for r in warm
             if r.get("steady_step_median_s")]
    out = {
        "experiment": exp,
        "category": records[0].get("category"),
        "n_measure": len(warm),
        "n_fresh": len(fresh),
        "warm_total_median_s": med(warm, "total_s"),
        "warm_ksampler_median_s": med(warm, None) if False else _med_field(warm, "ksampler_s"),
        "warm_vae_median_s": med(warm, "vae_decode_s"),
        "warm_step_median_s": round(statistics.median(steps), 3) if steps else None,
        "fresh_total_median_s": med(fresh, "total_s"),
        "fresh_text_encode_median_s": med(fresh, "text_encode_s"),
        "cold_total_s": cold[0]["runs"][0]["total_s"] if cold else None,
        "cold_server_boot_s": cold[0].get("server_boot_s") if cold else None,
        "vram_peak_mb": mx(records, "vram_peak_mb"),
        "vram_device_peak_mb": mx(records, "vram_device_peak_mb"),
        "gpu_util_pct_p50": _med_field(warm, "gpu_util_pct_p50"),
        "attention_backend": records[0].get("attention_backend"),
        "run_ids": sorted({r.get("session_id") for r in records}),
        "quality_status": _quality_status(exp),
    }
    return out


def _med_field(records: list[dict], field: str):
    vals = [r.get(field) for r in records if r.get(field) is not None]
    return round(statistics.median(vals), 3) if vals else None


def _quality_status(exp: str) -> str:
    q = lab_env.RESULTS_ROOT / "quality"
    verdicts = {}
    for f in sorted(q.glob(f"{exp}-quality.md")) if q.is_dir() else []:
        verdicts[f.name] = f.read_text(encoding="utf-8")[:200]
    if not verdicts:
        return "PENDING_HUMAN_REVIEW" if exp != "B0" else "REFERENCE"
    return "RECORDED"


def build(write: bool = False) -> dict:
    records = _load_records()
    by_exp: dict[str, list[dict]] = {}
    for r in records:
        by_exp.setdefault(r["experiment"], []).append(r)
    summary = {
        "generated_at": lab_env.build_snapshot()["created_at"],
        "n_records": len(records),
        "per_experiment": [summarize_experiment(rs) for _, rs in sorted(by_exp.items())],
    }
    if write:
        out = lab_env.RESULTS_ROOT
        out.mkdir(parents=True, exist_ok=True)
        (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (out / "SUMMARY.md").write_text(_markdown(summary), encoding="utf-8")
    return summary


def _markdown(s: dict) -> str:
    lines = [
        "# Linux W7900 lab — results summary (auto-generated)",
        "",
        f"Generated: {s['generated_at']}  ·  records: {s['n_records']}",
        "",
        "| Exp | Category | warm med (s) | step med (s) | fresh (s) | TE (s) | cold (s) | VRAM peak (MB) | util% p50 | attn | n | quality |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in s["per_experiment"]:
        lines.append(
            f"| {e['experiment']} | {e['category']} | {e['warm_total_median_s']} "
            f"| {e['warm_step_median_s']} | {e['fresh_total_median_s']} "
            f"| {e['fresh_text_encode_median_s']} | {e['cold_total_s']} "
            f"| {e['vram_device_peak_mb'] or e['vram_peak_mb']} "
            f"| {e['gpu_util_pct_p50']} | {e['attention_backend']} "
            f"| {e['n_measure']} | {e['quality_status']} |")
    return "\n".join(lines) + "\n"

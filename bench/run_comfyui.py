"""ComfyUI benchmark driver (protocol v1.3, manifest-driven).

Talks to an EXTERNAL ComfyUI server (bench/run_variant.ps1 owns its
lifecycle) over the HTTP API plus a /ws event monitor. Runs the frozen
matrix strictly sequentially (one queued prompt at a time) so wall times
never include queue waits. Every record field derives from the experiment
manifest (bench/experiments/<name>.json); the default manifest reproduces
the Phase 2 baseline byte-identically.

Timing semantics (protocol v1.3):
- total_s: wall time from prompt submission to history completion.
- denoise_s: server execution time (execution_start -> execution_success) —
  kept for Phase 2 continuity. CAVEAT (corrected 2026-10-31): measured runs
  differ from warmup only by seed, so CLIPTextEncode is a node-cache HIT and
  is excluded; the old report text claiming it "includes text encode" was
  wrong for measured runs. Real TE cost: text_encode_s from the ws monitor
  on cold/fresh runs.
- text_encode_s / vae_decode_s / ksampler_s / step_times_s: websocket
  per-node / per-step timing (RunMonitor in comfyui_client).
- vram_peak_mb: max of 0.5 s /system_stats sampling during the run (true
  peak); vram_residency_mb: post-run residency (the v1.2 metric, kept).
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow -I runs

from bench import comfyui_client  # noqa: E402
from bench.core import PROMPTS_PATH, REPO, plan_runs, validate_record  # noqa: E402
from bench.experiments import load_manifest  # noqa: E402


def order_specs(specs: list[dict]) -> list[dict]:
    """Execution order = plan order (sequential, no batching)."""
    if not specs:
        raise ValueError("empty plan")
    return list(specs)


def build_record(
    manifest: dict,
    spec: dict,
    *,
    total_s: float,
    execution_time_s: float,
    summary: dict,
    env_ref: str,
    session_id: str,
    restart_idx: int,
) -> dict:
    run_kind = spec["kind"]  # cold | warmup | measure | fresh_prompt
    record = {
        "experiment": manifest["experiment_name"],
        "phase": manifest["phase"],
        "framework": "comfyui",
        "precision": manifest["precision"],
        "width": spec["width"],
        "height": spec["height"],
        "steps": manifest["steps"],
        "seed": spec["seed"],
        "prompt_id": spec["prompt_id"],
        "protocol_version": "v1.3",
        "runs": [
            {
                "kind": "cold" if run_kind == "cold" else (
                    "fresh" if run_kind == "fresh_prompt" else "warm"
                ),
                "total_s": round(total_s, 3),
                "text_encode_s": summary["text_encode_s"],
                "denoise_s": round(execution_time_s, 3),
                "vae_decode_s": summary["vae_decode_s"],
                "step_times_s": summary["step_times_s"],
            }
        ],
        "vram_peak_mb": summary["vram_peak_mb"],
        "env_ref": env_ref,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_kind": run_kind,
        "attention_backend": manifest["attention_backend"],
        "execution_time_s": round(execution_time_s, 3),
        "sampler": manifest["sampler"],
        "scheduler": manifest["scheduler"],
        "cfg": manifest["cfg"],
        "ksampler_s": summary["ksampler_s"],
        "node_timings_s": summary["node_timings_s"],
        "cached_nodes": summary["cached_nodes"],
        "vram_residency_mb": summary["vram_residency_mb"],
        "unet": manifest["unet"],
        "clip": manifest["clip"],
        "vae": manifest["vae"],
        "weight_dtype": manifest["weight_dtype"],
        "tiled_vae": manifest["tiled_vae"],
        "session_id": session_id,
        "restart_idx": restart_idx,
    }
    if summary.get("monitor_error"):
        record["monitor_error"] = summary["monitor_error"]
    return record


def _env_ref() -> str:
    env_dir = REPO / "bench" / "results" / "env"
    snaps = sorted(env_dir.glob("snapshot-*.json")) if env_dir.is_dir() else []
    return snaps[-1].name if snaps else "unknown"


def _execute(base_url: str, wf: dict) -> tuple[float, float, dict, dict]:
    """Run one prompt with the RunMonitor attached; returns timing bundle."""
    mon = comfyui_client.RunMonitor(base_url)
    mon.start()
    try:
        t0 = time.perf_counter()
        prompt_id = comfyui_client.post_prompt(base_url, wf, client_id=mon.client_id)
        history = comfyui_client.wait_for_result(base_url, prompt_id)
        total_s = time.perf_counter() - t0
    finally:
        mon.stop()
    ts = {
        msg[0]: msg[1]["timestamp"]
        for msg in history.get("status", {}).get("messages", [])
        if len(msg) == 2 and isinstance(msg[1], dict) and "timestamp" in msg[1]
    }
    if "execution_start" in ts and "execution_success" in ts:
        execution_time_s = (ts["execution_success"] - ts["execution_start"]) / 1000.0
    else:
        execution_time_s = total_s
    return total_s, execution_time_s, mon.summarize(wf), history


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="results dir name under bench/results/")
    ap.add_argument("--experiment", default="p2-comfyui-1024x1024",
                    help="manifest name under bench/experiments/ (default: Phase 2 baseline)")
    ap.add_argument("--base-url", default="http://127.0.0.1:8188")
    ap.add_argument("--resolution", type=int, default=None,
                    help="override manifest resolution (2048 probes; name gets a suffix)")
    ap.add_argument("--session", default=None, help="session id (default: --date value)")
    ap.add_argument("--restart-idx", type=int, default=0)
    ns = ap.parse_args(sys.argv[1:])

    manifest = load_manifest(ns.experiment)
    res = ns.resolution or manifest["resolution"]
    manifest["experiment_name"] = (
        manifest["name"]
        if res == manifest["resolution"]
        else f"{manifest['name']}-{res}x{res}"
    )
    resolutions = [(res, res)]

    comfyui_client.check_server(ns.base_url)

    prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    prompt_text = {p["id"]: (p["prompt"], p["negative_prompt"]) for p in prompts["prompts"]}
    specs = order_specs(
        plan_runs(list(prompt_text), resolutions, prompts["seeds"],
                  measured=manifest["measured"])
    )

    def wf_for(prompt_id: str, seed: int, text_override: str | None = None):
        text, negative = prompt_text[prompt_id]
        if text_override is not None:
            text = text_override
        return comfyui_client.build_workflow(
            unet=manifest["unet"], clip=manifest["clip"], vae=manifest["vae"],
            prompt=text, negative=negative,
            width=res, height=res,
            steps=manifest["steps"], seed=seed,
            sampler=manifest["sampler"], scheduler=manifest["scheduler"],
            cfg=manifest["cfg"], weight_dtype=manifest["weight_dtype"],
            tiled_vae=manifest["tiled_vae"],
        )

    # one preflight on a representative workflow: node classes + model names
    first_prompt = next(iter(prompt_text))
    comfyui_client.preflight_workflow(
        ns.base_url, wf_for(first_prompt, seed=0)
    )

    results_dir = REPO / "bench" / "results" / ns.date
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = REPO / "results" / "raw" / ns.date
    session_id = ns.session or ns.date

    # fresh-prompt arm: same prompts with a neutral trailing period busts the
    # CLIPTextEncode node cache, so text_encode_s reflects the real TE cost
    # (measured runs are seed-only changes -> TE is always a cache hit there)
    if manifest.get("fresh_prompt_arm"):
        for prompt_id in prompt_text:
            specs.append({"kind": "fresh_prompt", "prompt_id": prompt_id,
                          "width": res, "height": res,
                          "seed": prompts["seeds"][0], "run_idx": 0})

    for spec in specs:
        text_override = None
        if spec["kind"] == "fresh_prompt":
            text_override = prompt_text[spec["prompt_id"]][0] + " ."
        wf = wf_for(spec["prompt_id"], spec["seed"], text_override=text_override)

        total_s, execution_time_s, summary, history = _execute(ns.base_url, wf)

        png = comfyui_client.fetch_image(ns.base_url, history)
        tag = spec["kind"] if spec["kind"] in ("cold", "warmup", "fresh_prompt") else (
            f"r{spec['run_idx']}"
        )
        out_png = raw_dir / f"{spec['prompt_id']}-{spec['seed']}-{tag}.png"
        out_png.parent.mkdir(parents=True, exist_ok=True)
        out_png.write_bytes(png)

        record = build_record(
            manifest, spec,
            total_s=total_s, execution_time_s=execution_time_s, summary=summary,
            env_ref=_env_ref(), session_id=session_id, restart_idx=ns.restart_idx,
        )
        validate_record(record)
        out_json = results_dir / f"{spec['prompt_id']}-{spec['seed']}-{tag}.json"
        out_json.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(
            f"{spec['kind']:13s} {record['experiment']} {spec['prompt_id']} "
            f"seed={spec['seed']} total={record['runs'][0]['total_s']}s "
            f"exec={record['runs'][0]['denoise_s']}s "
            f"te={record['runs'][0]['text_encode_s']}s "
            f"ks={record['ksampler_s']}s vae={record['runs'][0]['vae_decode_s']}s "
            f"cached={len(record['cached_nodes'])}",
            flush=True,
        )


if __name__ == "__main__":
    main()

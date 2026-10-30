"""Benchmark harness for the Phase 1 diffusers baseline (protocol v1).

Executes the full frozen matrix from ONE process so the pipeline is loaded
once (the "cold" run) and every subsequent run is warm:

  3 prompts x 2 resolutions (1024^2, 2048^2) x 40 steps
  per config: 1 warmup + 3 measured runs (one per frozen seed)

Writes one JSON per run (schema: bench/schema/result.schema.json) under
bench/results/<date>/<experiment>/, plus cold.json at the results root.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPTS = json.loads((REPO / "bench" / "prompts.json").read_text(encoding="utf-8"))
WEIGHTS_DIR = REPO / "weights" / "diffusers-format"
ENV_DIR = REPO / "bench" / "results" / "env"


def plan_runs(
    prompt_ids: list[str],
    resolutions: list[tuple[int, int]],
    seeds: list[int],
    warmup: int = 1,
    measured: int = 3,
) -> list[dict]:
    """Return ordered run specs: one cold first, then per config warmup+measures."""
    specs: list[dict] = []
    first = True
    for prompt_id in prompt_ids:
        for (w, h) in resolutions:
            if first:
                specs.append(
                    {"kind": "cold", "prompt_id": prompt_id, "width": w,
                     "height": h, "seed": seeds[0], "run_idx": 0}
                )
                first = False
            for _ in range(warmup):
                specs.append(
                    {"kind": "warmup", "prompt_id": prompt_id, "width": w,
                     "height": h, "seed": seeds[0], "run_idx": 0}
                )
            for i in range(measured):
                specs.append(
                    {"kind": "measure", "prompt_id": prompt_id, "width": w,
                     "height": h, "seed": seeds[i % len(seeds)], "run_idx": i}
                )
    return specs


def _env_ref() -> str:
    if ENV_DIR.is_dir():
        snaps = sorted(ENV_DIR.glob("snapshot-*.json"))
        if snaps:
            return snaps[-1].name
    return "unknown"


def _run_once(pipe, torch, spec, prompt, negative):
    step_times: list[float] = []
    t_last = {"t": None}

    def on_step_end(pipe_, i, t, kwargs):
        now = time.perf_counter()
        if t_last["t"] is not None:
            step_times.append(now - t_last["t"])
        t_last["t"] = now
        return kwargs

    generator = torch.Generator(device="cuda").manual_seed(spec["seed"])
    torch.cuda.reset_peak_memory_stats()
    t_last["t"] = time.perf_counter()  # so step 1 gets a duration too
    t0 = time.perf_counter()
    image = pipe(
        prompt=prompt,
        negative_prompt=negative or None,
        width=spec["width"],
        height=spec["height"],
        num_inference_steps=40,
        generator=generator,
        callback_on_step_end=on_step_end,
    ).images[0]
    total_s = time.perf_counter() - t0
    return image, {
        "kind": "cold" if spec["kind"] == "cold" else "warm",
        "total_s": round(total_s, 3),
        "text_encode_s": None,
        "denoise_s": round(float(sum(step_times)), 3),
        "vae_decode_s": None,
        "step_times_s": [round(s, 3) for s in step_times],
    }, round(torch.cuda.max_memory_allocated() / 2**20, 1)


def main() -> None:
    import os

    import torch
    from diffusers import QwenImage21Pipeline

    # Workaround for docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-
    # textencoder.md: accelerated SDPA backends hit hipErrorInvalidValue on
    # this stack; math backend validated working (attempt C).
    if os.environ.get("QIR_SDP") == "math":
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        print("note: math-only SDP forced (QIR_SDP=math)")

    print("loading pipeline...", flush=True)
    pipe = QwenImage21Pipeline.from_pretrained(str(WEIGHTS_DIR), torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()

    if os.environ.get("QIR_ATTENTION"):
        pipe.transformer.set_attention_backend(os.environ["QIR_ATTENTION"])
        print(f"note: DiT attention backend set to {os.environ['QIR_ATTENTION']}", flush=True)

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="results dir name under bench/results/")
    ns = ap.parse_args(sys.argv[1:])

    results_dir = REPO / "bench" / "results" / ns.date
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = REPO / "results" / "raw" / ns.date

    prompt_text = {p["id"]: (p["prompt"], p["negative_prompt"]) for p in PROMPTS["prompts"]}
    seeds = PROMPTS["seeds"]
    specs = plan_runs(list(prompt_text), [(1024, 1024), (2048, 2048)], seeds)

    for spec in specs:
        prompt, negative = prompt_text[spec["prompt_id"]]
        image, run, vram = _run_once(pipe, torch, spec, prompt, negative)
        experiment = f"p1-bf16-{spec['width']}x{spec['height']}"
        record = {
            "experiment": experiment,
            "phase": 1,
            "framework": "diffusers",
            "precision": "bf16",
            "width": spec["width"],
            "height": spec["height"],
            "steps": 40,
            "seed": spec["seed"],
            "prompt_id": spec["prompt_id"],
            "protocol_version": PROMPTS["protocol_version"],
            "runs": [run],
            "vram_peak_mb": vram,
            "env_ref": _env_ref(),
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "run_kind": spec["kind"],  # cold | warmup | measure (report filter)
        }
        if spec["kind"] == "cold":
            out_json = results_dir / "cold.json"
            out_png = raw_dir / experiment / "cold.png"
        else:
            tag = spec["kind"] if spec["kind"] == "warmup" else "r"
            suffix = tag if tag == "warmup" else f"r{spec['run_idx']}"
            out_json = (
                results_dir / experiment / f"{spec['prompt_id']}-{spec['seed']}-{suffix}.json"
            )
            out_png = raw_dir / experiment / f"{spec['prompt_id']}-{spec['seed']}-{suffix}.png"
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(record, indent=2), encoding="utf-8")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        image.save(out_png)
        print(f"{spec['kind']:8s} {experiment} {spec['prompt_id']} seed={spec['seed']} "
              f"total={run['total_s']}s denoise={run['denoise_s']}s vram={vram}MB", flush=True)


if __name__ == "__main__":
    main()

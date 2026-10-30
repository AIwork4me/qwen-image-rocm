"""Qwen-Image-2.1 generation CLI with stage timing (Phase 1, diffusers baseline).

Stage timing method (documented per plan):
- denoise: per-step wall times collected via ``callback_on_step_end``;
  ``denoise_s`` is their sum (always real).
- text_encode_s / vae_decode_s: ``null`` in this version — the pipeline does
  not expose them as separate component calls; they are first candidates to
  extract when the benchmark needs finer breakdowns.

Run (inside the phase1 venv):
    python -I phase1-diffusers/generate.py --prompt-id p1-zh-scene \
        --width 1024 --height 1024 --steps 4 --seed 42 --out results/raw/smoke
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROMPTS_PATH = Path(__file__).resolve().parents[1] / "bench" / "prompts.json"
WEIGHTS_DIR = Path(__file__).resolve().parents[1] / "weights" / "diffusers-format"
SCHEMA_ENV_DIR = Path(__file__).resolve().parents[1] / "bench" / "results" / "env"
EXPECTED_ARCH = "gfx1100"


def resolve_prompt(prompt_id: str) -> tuple[str, str]:
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    for p in data["prompts"]:
        if p["id"] == prompt_id:
            return p["prompt"], p["negative_prompt"]
    raise KeyError(prompt_id)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt-id", help="id from bench/prompts.json")
    src.add_argument("--prompt", help="literal prompt text")
    parser.add_argument("--width", type=int, default=2048)
    parser.add_argument("--height", type=int, default=2048)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="results/raw/")
    parser.add_argument("--precision", choices=["bf16"], default="bf16")
    return parser.parse_args(argv)


def _env_ref() -> str:
    if SCHEMA_ENV_DIR.is_dir():
        snaps = sorted(SCHEMA_ENV_DIR.glob("snapshot-*.json"))
        if snaps:
            return snaps[-1].name
    return "unknown"


def _check_device(torch) -> None:
    if not torch.cuda.is_available():
        sys.exit("ERROR: torch.cuda unavailable (no usable HIP runtime)")
    props = torch.cuda.get_device_properties(0)
    arch = getattr(props, "gcnArchName", "").split(":")[0]
    if EXPECTED_ARCH not in arch:
        sys.exit(f"ERROR: device arch '{arch}', expected '{EXPECTED_ARCH}'")


def main() -> None:
    import torch  # heavy imports stay lazy so tests can import this module
    from diffusers import QwenImage21Pipeline

    ns = parse_args(sys.argv[1:])
    if ns.prompt_id:
        prompt, negative = resolve_prompt(ns.prompt_id)
        prompt_id = ns.prompt_id
    else:
        prompt, negative = ns.prompt, ""
        prompt_id = "literal"
    _check_device(torch)

    pipe = QwenImage21Pipeline.from_pretrained(
        str(WEIGHTS_DIR), torch_dtype=torch.bfloat16
    )
    pipe.enable_model_cpu_offload()

    step_times: list[float] = []
    t_last = {"t": None}

    def on_step_end(pipe_, i, t, kwargs):
        now = time.perf_counter()
        if t_last["t"] is not None:
            step_times.append(now - t_last["t"])
        t_last["t"] = now
        return kwargs

    generator = torch.Generator(device="cuda").manual_seed(ns.seed)
    t0 = time.perf_counter()
    image = pipe(
        prompt=prompt,
        negative_prompt=negative or None,
        width=ns.width,
        height=ns.height,
        num_inference_steps=ns.steps,
        generator=generator,
        callback_on_step_end=on_step_end,
    ).images[0]
    total_s = time.perf_counter() - t0
    denoise_s = float(sum(step_times))

    experiment = f"p1-{ns.precision}-{ns.width}x{ns.height}"
    out_dir = Path(ns.out) / experiment
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{ns.seed}-{int(time.time())}"
    png_path = out_dir / f"{stem}.png"
    image.save(png_path)

    result = {
        "experiment": experiment,
        "phase": 1,
        "framework": "diffusers",
        "precision": ns.precision,
        "width": ns.width,
        "height": ns.height,
        "steps": ns.steps,
        "seed": ns.seed,
        "prompt_id": prompt_id,
        "protocol_version": "v1",
        "runs": [
            {
                "kind": "cold",
                "total_s": round(total_s, 3),
                "text_encode_s": None,
                "denoise_s": round(denoise_s, 3),
                "vae_decode_s": None,
                "step_times_s": [round(s, 3) for s in step_times],
            }
        ],
        "vram_peak_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "env_ref": _env_ref(),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "output_image": str(png_path),
    }
    sidecar = out_dir / f"{stem}.json"
    sidecar.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

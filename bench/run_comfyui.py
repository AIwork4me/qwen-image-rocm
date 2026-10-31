"""ComfyUI benchmark driver (protocol v1.1, Phase 2).

Talks to an EXTERNAL ComfyUI server (start it with
phase2-comfyui/launch_comfyui.ps1) over the HTTP API. Runs the frozen
matrix strictly sequentially (one queued prompt at a time) so wall times
never include queue waits behind other work.

Timing notes:
- total_s: wall time from prompt submission to history completion.
- execution_time_s: ComfyUI's own execution time from the history entry;
  recorded as denoise_s (approximation — includes text encode + VAE decode
  inside the server; disclosed in the report Limitations).
- step_times_s: empty (ComfyUI does not expose per-step times via API).
"""

import argparse
import json
import sys
import time
from datetime import datetime

from bench import comfyui_client
from bench.core import PROMPTS_PATH, REPO, plan_runs, validate_record

SAMPLER = "euler"
SCHEDULER = "simple"
UNET = "qwen_image_2.1_bf16.safetensors"
CLIP = "qwen3vl_8b_bf16.safetensors"
VAE = "qwen_image_2.1_vae_bf16.safetensors"


def order_specs(specs: list[dict]) -> list[dict]:
    """Execution order = plan order (sequential, no batching)."""
    if not specs:
        raise ValueError("empty plan")
    return list(specs)


def build_record(
    spec: dict,
    *,
    total_s: float,
    execution_time_s: float,
    vram_peak_mb: float,
    env_ref: str,
) -> dict:
    return {
        "experiment": f"p2-comfyui-{spec['width']}x{spec['height']}",
        "phase": 2,
        "framework": "comfyui",
        "precision": "bf16",
        "width": spec["width"],
        "height": spec["height"],
        "steps": 40,
        "seed": spec["seed"],
        "prompt_id": spec["prompt_id"],
        "protocol_version": "v1",
        "runs": [
            {
                "kind": "cold" if spec["kind"] == "cold" else "warm",
                "total_s": round(total_s, 3),
                "text_encode_s": None,
                "denoise_s": round(execution_time_s, 3),
                "vae_decode_s": None,
                "step_times_s": [],
            }
        ],
        "vram_peak_mb": round(vram_peak_mb, 1),
        "env_ref": env_ref,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_kind": spec["kind"],
        "attention_backend": "comfyui-default",
        "execution_time_s": round(execution_time_s, 3),
        "sampler": SAMPLER,
        "scheduler": SCHEDULER,
    }


def _env_ref() -> str:
    env_dir = REPO / "bench" / "results" / "env"
    snaps = sorted(env_dir.glob("snapshot-*.json")) if env_dir.is_dir() else []
    return snaps[-1].name if snaps else "unknown"


def _server_vram_mb(base_url: str) -> float:
    stats = comfyui_client._get(f"{base_url}/system_stats").json()
    for d in stats.get("devices", []):
        if "7900" in (d.get("name") or ""):
            free = d.get("vram_free", 0)
            total = d.get("vram_total", 0)
            return round((total - free) / 2**20, 1)
    return 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True)
    ap.add_argument("--resolutions", default="1024")
    ap.add_argument("--base-url", default="http://127.0.0.1:8188")
    ns = ap.parse_args(sys.argv[1:])
    resolutions = [(int(r), int(r)) for r in ns.resolutions.split(",")]

    comfyui_client.check_server(ns.base_url)

    prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    prompt_text = {p["id"]: (p["prompt"], p["negative_prompt"]) for p in prompts["prompts"]}
    specs = order_specs(plan_runs(list(prompt_text), resolutions, prompts["seeds"]))

    results_dir = REPO / "bench" / "results" / ns.date
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = REPO / "results" / "raw" / ns.date

    for spec in specs:
        text, negative = prompt_text[spec["prompt_id"]]
        wf = comfyui_client.build_workflow(
            unet=UNET, clip=CLIP, vae=VAE,
            prompt=text, negative=negative,
            width=spec["width"], height=spec["height"],
            steps=40, seed=spec["seed"],
            sampler=SAMPLER, scheduler=SCHEDULER,
        )
        t0 = time.perf_counter()
        prompt_id = comfyui_client.post_prompt(ns.base_url, wf)
        history = comfyui_client.wait_for_result(ns.base_url, prompt_id)
        total_s = time.perf_counter() - t0
        ts = {
            msg[0]: msg[1]["timestamp"]
            for msg in history.get("status", {}).get("messages", [])
            if len(msg) == 2 and isinstance(msg[1], dict) and "timestamp" in msg[1]
        }
        if "execution_start" in ts and "execution_success" in ts:
            execution_time_s = (ts["execution_success"] - ts["execution_start"]) / 1000.0
        else:
            execution_time_s = total_s

        png = comfyui_client.fetch_image(ns.base_url, history)
        tag = "cold" if spec["kind"] == "cold" else (
            spec["kind"] if spec["kind"] == "warmup" else f"r{spec['run_idx']}"
        )
        out_png = raw_dir / f"{spec['prompt_id']}-{spec['seed']}-{tag}.png"
        out_png.parent.mkdir(parents=True, exist_ok=True)
        out_png.write_bytes(png)

        record = build_record(
            spec,
            total_s=total_s,
            execution_time_s=execution_time_s,
            vram_peak_mb=_server_vram_mb(ns.base_url),
            env_ref=_env_ref(),
        )
        validate_record(record)
        out_json = results_dir / f"{spec['prompt_id']}-{spec['seed']}-{tag}.json"
        out_json.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(
            f"{spec['kind']:8s} {record['experiment']} {spec['prompt_id']} "
            f"seed={spec['seed']} total={record['runs'][0]['total_s']}s "
            f"exec={record['runs'][0]['denoise_s']}s",
            flush=True,
        )


if __name__ == "__main__":
    main()

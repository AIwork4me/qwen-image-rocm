"""Minimal ComfyUI HTTP API client for benchmarking.

Pure functions (build_workflow) are importable without requests; HTTP
helpers import requests lazily. Workflow node classes are the standard
ComfyUI API-format set; sampler/scheduler/cfg defaults follow the official
Qwen-Image-2.1 template (euler / simple / cfg 1, no prompt rewriter —
fairness: raw prompts in both frameworks).
"""

import time
import uuid


def build_workflow(
    *,
    unet: str,
    clip: str,
    vae: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    steps: int,
    seed: int,
    sampler: str,
    scheduler: str,
) -> dict:
    def nid(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    unet_id, clip_id, vae_id = nid("unet"), nid("clip"), nid("vae")
    pos_id, neg_id = nid("pos"), nid("neg")
    latent_id, ks_id, dec_id, save_id = (
        nid("latent"), nid("ks"), nid("dec"), nid("save"),
    )
    return {
        unet_id: {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet, "weight_dtype": "default"},
        },
        clip_id: {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": clip, "type": "qwen_image"},
        },
        vae_id: {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae},
        },
        pos_id: {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": [clip_id, 0]},
        },
        neg_id: {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": [clip_id, 0]},
        },
        latent_id: {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        ks_id: {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": [unet_id, 0],
                "positive": [pos_id, 0],
                "negative": [neg_id, 0],
                "latent_image": [latent_id, 0],
            },
        },
        dec_id: {
            "class_type": "VAEDecode",
            "inputs": {"samples": [ks_id, 0], "vae": [vae_id, 0]},
        },
        save_id: {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "qir_bench", "images": [dec_id, 0]},
        },
    }


def _get(url: str, timeout: int = 10):
    import requests

    return requests.get(url, timeout=timeout)


def check_server(base_url: str) -> None:
    """Abort unless the server reports the target AMD GPU (anti CPU-fallback)."""
    stats = _get(f"{base_url}/system_stats").json()
    devices = stats.get("devices", [])
    if not any("7900" in (d.get("name") or "") for d in devices):
        raise RuntimeError(
            f"no AMD 7900 device in /system_stats: {devices} — refusing to benchmark"
        )


def post_prompt(base_url: str, workflow: dict) -> str:
    import requests

    r = requests.post(f"{base_url}/prompt", json={"prompt": workflow}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"comfyui rejected workflow: {body['error']}")
    return body["prompt_id"]


def wait_for_result(base_url: str, prompt_id: str, timeout_s: int = 1800) -> dict:
    import requests

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        hist = requests.get(f"{base_url}/history/{prompt_id}", timeout=30).json()
        entry = hist.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                raise RuntimeError(f"comfyui execution error: {msgs}")
            return entry
        time.sleep(1.0)
    raise TimeoutError(f"no result for {prompt_id} within {timeout_s}s")


def fetch_image(base_url: str, history: dict) -> bytes:
    import requests

    for node_out in history.get("outputs", {}).values():
        for img in node_out.get("images", []):
            r = requests.get(
                f"{base_url}/view",
                params={
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.content
    raise RuntimeError("no image in history outputs")

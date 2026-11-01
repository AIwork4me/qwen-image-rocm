"""Quickstart profiles: the only two user-facing generation configs.

Fast and Quality map to frozen experiment manifests (single source of truth:
``bench/experiments/``) plus the exact weight files each mode needs, so the
one-command path cannot drift from what was actually measured and quality-
gated. PowerShell glue (``quickstart.ps1``) consumes this module through its
small CLI; tests pin the mapping (tests/test_quickstart.py).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow -I runs

from bench.experiments import load_manifest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
WEIGHTS_ROOT = REPO / "weights" / "comfyui-split"

# Exact byte sizes of the frozen checkpoints (measured from the verified
# local copies; the authoritative sha256 comes from the host's LFS pointer
# at verify time — we never invent hashes). Sizes gate "already downloaded"
# and truncation checks.
WEIGHTS: dict[str, int] = {
    "diffusion_models/qwen_image_2.1_bf16.safetensors": 14_230_280_616,
    "diffusion_models/qwen_image_2.1_int8_convrot.safetensors": 7_256_783_064,
    "diffusion_models/qwen_image_2.1_turbo_bf16.safetensors": 14_230_280_616,
    "diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors": 7_256_787_829,
    "text_encoders/qwen3vl_8b_bf16.safetensors": 17_534_334_616,
    "text_encoders/qwen3vl_8b_int8_convrot.safetensors": 9_350_798_360,
    "text_encoders/qwen3vl_8b_w4a8.safetensors": 6_312_105_364,
    "vae/qwen_image_2.1_vae_bf16.safetensors": 675_509_688,
}

MODES = {
    # The full recommended production combo, measured as a whole 2026-11-01
    # (bench/results/2026-11-01-r1-triple/): Turbo 8-step int8 DiT + int8 TE
    # + ck attention + --disable-smart-memory.
    "fast": {
        "manifest": "p4-qs-fast-1024x1024",
        "resolutions": (1024, 2048),
        "weights": (
            "diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors",
            "text_encoders/qwen3vl_8b_int8_convrot.safetensors",
            "vae/qwen_image_2.1_vae_bf16.safetensors",
        ),
    },
    # Bit-identical to the phase-3 bf16 baseline (p3-vram-nosmart: LPIPS
    # 0.0000 vs control) with the measured --disable-smart-memory gain.
    "quality": {
        "manifest": "p4-qs-quality-1024x1024",
        "resolutions": (1024,),
        "weights": (
            "diffusion_models/qwen_image_2.1_bf16.safetensors",
            "text_encoders/qwen3vl_8b_bf16.safetensors",
            "vae/qwen_image_2.1_vae_bf16.safetensors",
        ),
    },
}


def config_for(mode: str) -> dict:
    """Mode -> {manifest fields..., resolutions, weights}; ValueError on typo."""
    try:
        cfg = MODES[mode.lower()]
    except KeyError:
        raise ValueError(
            f"unknown mode {mode!r} (available: {', '.join(sorted(MODES))})"
        ) from None
    out = dict(load_manifest(cfg["manifest"]))
    out["resolutions"] = cfg["resolutions"]
    out["weights"] = cfg["weights"]
    return out


def check_resolution(mode: str, resolution: int) -> None:
    cfg = MODES[mode.lower()]
    if resolution not in cfg["resolutions"]:
        if mode.lower() == "quality" and resolution == 2048:
            raise ValueError(
                "Quality mode at 2048 is not supported: bf16 VAE decode "
                "allocates a 20.25 GB conv tensor and OOMs on 24 GB cards "
                "(docs/issues/evidence/sdpa-7140-2048-vae-oom.log). Use "
                "-Mode Fast for 2048."
            )
        raise ValueError(
            f"resolution {resolution} not validated for mode {mode!r} "
            f"(tested: {', '.join(str(r) for r in cfg['resolutions'])})"
        )


def weights_state(mode: str) -> list[dict]:
    """Per-file state for the mode's weights: present/absent/truncated."""
    states = []
    for rel in MODES[mode.lower()]["weights"]:
        path = WEIGHTS_ROOT / rel
        expected = WEIGHTS[rel]
        if not path.exists():
            state = "absent"
        elif path.stat().st_size != expected:
            state = "truncated"
        else:
            state = "present"
        states.append({"rel": rel, "path": path, "expected_bytes": expected,
                       "state": state})
    return states


def _lfs_pointer(url_base: str, rel: str) -> dict:
    import requests

    pointer_url = f"{url_base.rstrip('/')}/raw/main/{rel}"
    r = requests.get(pointer_url, timeout=60)
    r.raise_for_status()
    oid = size = None
    for line in r.text.splitlines():
        if line.startswith("oid sha256:"):
            oid = line.split(":", 1)[1].strip()
        elif line.startswith("size "):
            size = int(line.split(None, 1)[1].strip())
    if not oid or size is None:
        raise ValueError(f"not an LFS pointer: {pointer_url}")
    return {"sha256": oid, "size": size}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_weight(rel: str, url_base: str) -> dict:
    """Authoritative integrity check: sha256+size from the host's LFS
    pointer vs the local file. Returns a report; never raises on mismatch
    (mismatch is reported as ok=false)."""
    path = WEIGHTS_ROOT / rel
    if rel not in WEIGHTS:
        raise ValueError(f"unknown weight {rel!r}")
    info = _lfs_pointer(url_base, rel)
    local_size = path.stat().st_size if path.exists() else 0
    size_ok = local_size == info["size"]
    sha_ok = size_ok and _sha256(path) == info["sha256"]
    return {"rel": rel, "expected_size": info["size"], "local_size": local_size,
            "size_ok": size_ok, "sha256_ok": sha_ok,
            "ok": size_ok and sha_ok}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["config", "weights-state", "verify-weight"])
    ap.add_argument("--mode", default=None, help="fast | quality")
    ap.add_argument("--rel", default=None, help="weight path relative to weights root")
    ap.add_argument(
        "--url-base",
        default="https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1",
        help="HF repo base URL (respects HF_ENDPOINT-style mirrors)",
    )
    ns = ap.parse_args(sys.argv[1:])

    if ns.command == "config":
        print(json.dumps(config_for(ns.mode or "fast"), indent=2))
    elif ns.command == "weights-state":
        print(json.dumps(weights_state(ns.mode or "fast"), indent=2, default=str))
    else:
        print(json.dumps(verify_weight(ns.rel, ns.url_base), indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()

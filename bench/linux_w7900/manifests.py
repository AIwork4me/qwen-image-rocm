"""Linux W7900 lab experiment manifests: ``bench/linux_w7900/experiments/``.

Data-driven, same spirit as ``bench/experiments.py`` but with the lab's own
experiment IDs (B0/L1/F1/F2/LF*/H*/BEST — the methodology matrix) and
Linux-specific fields:

- ``sdp_mode``: "none" (default) = normal functional Linux attention
  (ComfyUI's aotriton probe picks pytorch attention on this stack);
  "math" only as a separately-labeled diagnostic variant.
- ``server_flags``: extra ComfyUI CLI args (attention / vram modes).
- ``attention_backend``: what the manifest INTENDS (verified against the
  server log after the run; never trusted blindly).

The frozen protocol is reused unchanged from ``bench/prompts.json``
(3 prompts x seeds [42, 1337, 20261030], euler/simple, cfg 1.0).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import lab_env

EXPERIMENTS_DIR = lab_env.LAB / "experiments"

REQUIRED_FIELDS = (
    "id", "category", "description", "framework", "precision",
    "resolution", "steps", "cfg", "sampler", "scheduler",
    "unet", "clip", "vae", "weight_dtype", "tiled_vae",
    "attention_backend", "measured",
)
OPTIONAL_DEFAULTS = {
    "server_flags": [],
    "sdp_mode": "none",  # Linux default: normal attention, no math forcing
    "env_vars": {},
    "attention_log_patterns": None,  # server.py defaults
    "fresh_prompt_arm": False,
    "scheduler_note": "",
    "enabled": True,
}

_ID_RE = re.compile(r"[A-Z]\d*[a-z0-9-]*")  # B0, L1, F1, LF1, LF3, H1, H2, BEST, ...

KNOWN_IDS = ("B0", "L1", "L1O", "F1", "F2", "LF1", "LF2", "LF3", "H1", "H2", "BEST")


def validate_manifest(m: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in m]
    if missing:
        raise ValueError(f"manifest {m.get('id', '?')!r} missing fields: {missing}")
    if m["id"] not in KNOWN_IDS:
        raise ValueError(
            f"experiment id {m['id']!r} not in the methodology matrix {KNOWN_IDS} "
            "— never silently substitute a different optimization")
    if m["framework"] != "comfyui":
        raise ValueError("linux lab manifests are comfyui-only")
    if m.get("sdp_mode", "none") == "math" and m["id"] == "B0":
        raise ValueError("B0 must use the normal Linux attention (sdp_mode=none); "
                         "math forcing is a separate diagnostic variant")


def load_manifest(name: str) -> dict:
    path = EXPERIMENTS_DIR / f"{name}.json"
    if not path.is_file():
        available = sorted(p.stem for p in EXPERIMENTS_DIR.glob("*.json"))
        raise FileNotFoundError(
            f"no manifest {name!r} under bench/linux_w7900/experiments/ (available: {available})")
    m = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(m)
    merged = dict(m)
    for key, default in OPTIONAL_DEFAULTS.items():
        merged.setdefault(key, default)
    return merged


def list_manifests() -> list[str]:
    return sorted(p.stem for p in EXPERIMENTS_DIR.glob("*.json"))

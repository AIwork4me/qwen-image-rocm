"""Phase 3 experiment manifests: ``bench/experiments/<name>.json``.

One file per variant; the ComfyUI driver derives every record field from its
manifest (single ``--experiment`` entry point instead of flag soup).
``p2-comfyui-1024x1024.json`` reproduces the Phase 2 baseline byte-identically
(guarded by tests/test_experiments.py), so historical numbers stay
reproducible while new variants are pure data.

Server-facing fields are consumed by bench/run_variant.ps1:
- ``server_flags``: extra ComfyUI CLI args (attention / vram / cache modes)
- ``sdp_mode``: math | none | math-hard — launch_wrapper.py modes.
  ``math-hard`` neuters ComfyUI's own re-enable of accelerated SDPA
  (model_management.py:547-550 fires when --use-pytorch-cross-attention is
  set, silently undoing the plain math workaround).
- ``env_vars``: extra environment variables for the server process.
- ``attention_log_patterns``: regex list; any server-log match is captured as
  evidence of the ACTUAL attention path (never trust the launch flags alone).
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow -I runs

from bench.core import REPO  # noqa: E402

EXPERIMENTS_DIR = REPO / "bench" / "experiments"

REQUIRED_FIELDS = (
    "name", "phase", "description", "framework", "precision",
    "resolution", "steps", "cfg", "sampler", "scheduler",
    "unet", "clip", "vae", "weight_dtype", "tiled_vae",
    "attention_backend", "measured",
)
OPTIONAL_DEFAULTS = {
    "server_flags": [],
    "sdp_mode": "math",
    "env_vars": {},
    "attention_log_patterns": ["attention|quadratic|disabling"],
    "fresh_prompt_arm": False,
}

_NAME_RE = re.compile(r"p\d-[a-z0-9]+(-[a-z0-9]+)*-\d+x\d+")


def validate_manifest(m: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in m]
    if missing:
        raise ValueError(f"manifest {m.get('name', '?')!r} missing fields: {missing}")
    if not _NAME_RE.fullmatch(m["name"]):
        raise ValueError(
            f"experiment name {m['name']!r} must match p{{phase}}-{{lever}}-{{W}}x{{H}}"
        )
    if m["framework"] != "comfyui":
        raise ValueError("only comfyui manifests are defined here (diffusers uses env vars)")
    if (
        "--use-pytorch-cross-attention" in m.get("server_flags", [])
        and m.get("sdp_mode", "math") != "math-hard"
    ):
        raise ValueError(
            "--use-pytorch-cross-attention re-enables accelerated SDPA "
            "(model_management.py:547); this variant must set sdp_mode=math-hard"
        )


def load_manifest(name: str) -> dict:
    path = EXPERIMENTS_DIR / f"{name}.json"
    if not path.is_file():
        available = sorted(p.stem for p in EXPERIMENTS_DIR.glob("*.json"))
        raise FileNotFoundError(
            f"no manifest {name!r} under bench/experiments/ (available: {available})"
        )
    m = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(m)
    merged = dict(m)
    for key, default in OPTIONAL_DEFAULTS.items():
        merged.setdefault(key, default)
    return merged


def list_manifests() -> list[str]:
    return sorted(p.stem for p in EXPERIMENTS_DIR.glob("*.json"))

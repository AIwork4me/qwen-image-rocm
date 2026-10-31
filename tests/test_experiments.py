"""Guards for the Phase 3 experiment-manifest system.

The key invariant: the p2 manifest must reproduce the Phase 2 baseline
byte-identically (modulo randomized node ids) so every historical number
stays reproducible while new variants are pure data files.
"""

import json

import pytest

from bench.comfyui_client import build_workflow
from bench.experiments import (
    EXPERIMENTS_DIR,
    list_manifests,
    load_manifest,
    validate_manifest,
)

# pre-Phase-3 constants from run_comfyui.py (kept here as the frozen oracle)
LEGACY = {
    "unet": "qwen_image_2.1_bf16.safetensors",
    "clip": "qwen3vl_8b_bf16.safetensors",
    "vae": "qwen_image_2.1_vae_bf16.safetensors",
    "steps": 40,
    "cfg": 1.0,
    "sampler": "euler",
    "scheduler": "simple",
}


def _canonical(wf: dict) -> list:
    """Structure-only view: node ids (incl. link targets) replaced by class."""
    cls = {nid: node["class_type"] for nid, node in wf.items()}

    def norm(v):
        if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] in cls:
            return [cls[v[0]], v[1]]
        return v

    return sorted(
        (node["class_type"], sorted((k, json.dumps(norm(v))) for k, v in node["inputs"].items()))
        for node in wf.values()
    )


def test_all_manifests_validate():
    paths = sorted(EXPERIMENTS_DIR.glob("*.json"))
    assert len(paths) >= 19, "expected the full Phase 3 variant set"
    for p in paths:
        m = json.loads(p.read_text(encoding="utf-8"))
        validate_manifest(m)  # no raise
        assert m["name"] == p.stem, f"{p.name}: name field must equal file stem"


def test_manifest_loading_errors():
    with pytest.raises(FileNotFoundError, match="available"):
        load_manifest("no-such-experiment")
    assert "p2-comfyui-1024x1024" in list_manifests()


def test_validate_manifest_rules():
    with pytest.raises(ValueError, match="missing fields"):
        validate_manifest({"name": "p3-x-1024x1024"})
    with pytest.raises(ValueError, match="p\\{phase\\}"):
        split = json.loads((EXPERIMENTS_DIR / "p3-attn-split-1024x1024.json").read_text())
        validate_manifest({**split, "name": "bad-name"})
    # pytorch-cross-attention without math-hard would silently re-arm the
    # hipErrorInvalidValue path (model_management.py:547-550)
    m = json.loads((EXPERIMENTS_DIR / "p3-attn-pytorch-math-1024x1024.json").read_text())
    with pytest.raises(ValueError, match="math-hard"):
        validate_manifest({**m, "sdp_mode": "math"})


def test_p2_manifest_reproduces_phase2_baseline():
    m = load_manifest("p2-comfyui-1024x1024")
    assert m["phase"] == 2
    assert m["precision"] == "bf16"
    for key, value in LEGACY.items():
        assert m[key] == value, f"p2 manifest drifted from Phase 2 constants: {key}"
    assert m["weight_dtype"] == "default"
    assert m["tiled_vae"] is False
    assert m["attention_backend"] == "comfyui-default"
    assert m["server_flags"] == []
    assert m["sdp_mode"] == "math"  # launch_comfyui.ps1 default since Phase 2
    assert m["measured"] == 3

    wf_manifest = build_workflow(
        unet=m["unet"], clip=m["clip"], vae=m["vae"], prompt="p", negative="n",
        width=1024, height=1024, steps=m["steps"], seed=42,
        sampler=m["sampler"], scheduler=m["scheduler"], cfg=m["cfg"],
        weight_dtype=m["weight_dtype"], tiled_vae=m["tiled_vae"],
    )
    wf_legacy = build_workflow(
        unet=LEGACY["unet"], clip=LEGACY["clip"], vae=LEGACY["vae"],
        prompt="p", negative="n", width=1024, height=1024,
        steps=LEGACY["steps"], seed=42,
        sampler=LEGACY["sampler"], scheduler=LEGACY["scheduler"],
    )
    assert _canonical(wf_manifest) == _canonical(wf_legacy)


def test_variant_manifests_reference_expected_weights():
    turbo = load_manifest("p3-turbo-8step-1024x1024")
    assert turbo["unet"] == "qwen_image_2.1_turbo_bf16.safetensors"
    assert turbo["steps"] == 8
    assert turbo["fresh_prompt_arm"] is True  # TE cost visible for the 8-step model
    quant = load_manifest("p3-int8-dit-te-1024x1024")
    assert quant["unet"] == "qwen_image_2.1_int8_convrot.safetensors"
    assert quant["clip"] == "qwen3vl_8b_int8_convrot.safetensors"
    assert quant["weight_dtype"] == "default"  # native quant: metadata-detected
    tiled = load_manifest("p3-vaetiled-1024x1024")
    assert tiled["tiled_vae"] is True and tiled["measured"] == 5  # <10% effect -> n=5

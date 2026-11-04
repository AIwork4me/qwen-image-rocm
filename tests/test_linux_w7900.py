"""CPU-only guards for the Linux W7900 lab (no GPU needed, mirrors CI gate).

Covers: manifest validation, record schema conformance, kernel classifier,
report aggregation, and CLI importability. GPU validation is performed
separately on the physical W7900 (docs/linux-w7900/).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.core import validate_record
from bench.linux_w7900 import lab_env, manifests
from bench.linux_w7900.report import summarize_experiment
from bench.linux_w7900.runner import build_record


def test_all_lab_manifests_load_and_validate():
    ids = manifests.list_manifests()
    assert ids, "no linux lab manifests found"
    for mid in ids:
        m = manifests.load_manifest(mid)
        assert m["id"] == mid
        assert m["framework"] == "comfyui"
        assert m["cfg"] == 1.0 and m["sampler"] == "euler"
        # protocol essentials shared with the frozen Windows protocol
        assert m["clip"] == "qwen3vl_8b_bf16.safetensors"
        assert m["vae"] == "qwen_image_2.1_vae_bf16.safetensors"


def test_manifest_rejects_unknown_id(tmp_path):
    bad = tmp_path / "XX9.json"
    bad.write_text(json.dumps({
        "id": "XX9", "category": "other", "description": "x",
        "framework": "comfyui", "precision": "bf16", "resolution": 1024,
        "steps": 1, "cfg": 1.0, "sampler": "euler", "scheduler": "simple",
        "unet": "u", "clip": "c", "vae": "v", "weight_dtype": "default",
        "tiled_vae": False, "attention_backend": "x", "measured": 1}))
    monkey_dir = manifests.EXPERIMENTS_DIR
    try:
        manifests.EXPERIMENTS_DIR = tmp_path
        with pytest.raises(ValueError, match="methodology matrix"):
            manifests.load_manifest("XX9")
    finally:
        manifests.EXPERIMENTS_DIR = monkey_dir


def test_b0_uses_normal_attention():
    m = manifests.load_manifest("B0")
    assert m["sdp_mode"] == "none"
    assert m["steps"] == 40 and m["unet"] == "qwen_image_2.1_bf16.safetensors"


def test_b0_math_forcing_rejected(tmp_path, monkeypatch):
    m = manifests.load_manifest("B0")
    m = dict(m)
    m["sdp_mode"] = "math"
    with pytest.raises(ValueError, match="normal Linux attention"):
        manifests.validate_manifest(m)


def test_build_record_schema_valid():
    m = manifests.load_manifest("B0")
    summary = {
        "text_encode_s": 0.5, "vae_decode_s": 0.9, "ksampler_s": 53.9,
        "step_times_s": [1.5] + [1.35] * 39, "node_timings_s": {}, "cached_nodes": [],
        "vram_peak_mb": 33000.0, "vram_residency_mb": 32000.0,
        "monitor_error": None, "vram_device_peak_mb": 34000.0,
        "gpu_util_pct_p50": 99.0, "gpu_util_pct_max": 100.0,
    }
    rec = build_record(m, {"kind": "measure", "prompt_id": "p1-zh-scene",
                           "width": 1024, "height": 1024, "seed": 42, "run_idx": 0},
                       total_s=55.5, execution_time_s=55.0, summary=summary,
                       env_ref="snapshot-test.json", run_id="test-B0",
                       server_boot_s=None, attention_evidence={})
    validate_record(rec)  # raises on violation
    assert rec["lab"] == "linux-w7900"
    assert rec["steady_step_median_s"] == 1.35  # step[0] excluded
    assert rec["runs"][0]["kind"] == "warm"


def test_summarize_experiment():
    m = manifests.load_manifest("B0")
    summary = {
        "text_encode_s": 0.5, "vae_decode_s": 0.9, "ksampler_s": 53.9,
        "step_times_s": [1.5] + [1.35] * 39, "node_timings_s": {}, "cached_nodes": [],
        "vram_peak_mb": 33000.0, "vram_residency_mb": 32000.0, "monitor_error": None,
    }
    recs = []
    for i, kind in enumerate(["cold", "measure", "measure", "measure", "fresh_prompt"]):
        recs.append(build_record(
            m, {"kind": kind, "prompt_id": "p1-zh-scene", "width": 1024,
                "height": 1024, "seed": 42, "run_idx": i},
            total_s=75.0 if kind == "cold" else (57.0 if kind == "fresh_prompt" else 55.5),
            execution_time_s=55.0, summary=summary,
            env_ref="s.json", run_id="t", server_boot_s=None,
            attention_evidence={}))
    s = summarize_experiment(recs)
    assert s["experiment"] == "B0"
    assert s["n_measure"] == 3
    assert s["warm_total_median_s"] == 55.5
    assert s["fresh_total_median_s"] == 57.0
    assert s["cold_total_s"] == 75.0


def test_kernel_classifier():
    from bench.linux_w7900.profile import _classify_kernel as c
    assert c("void hipblasLt::gemm_tune_xdlops") == "gemm"
    assert c("void fmha_fwd_kernel_mfma") == "attention"
    assert c("at::native::vectorized_elementwise_kernel") == "elementwise/activation"
    assert c("at::native::layer_norm_kernel") == "norm"
    assert c("some_unknown_kernel") == "other"


def test_cli_importable():
    from bench.linux_w7900.__main__ import main
    with pytest.raises(SystemExit):
        main(["--help"])


def test_lab_results_use_separate_root():
    assert "linux-w7900" in str(lab_env.RESULTS_ROOT)
    assert lab_env.RESULTS_ROOT.name == "linux-w7900"
    assert lab_env.RESULTS_ROOT.parent.name == "results"

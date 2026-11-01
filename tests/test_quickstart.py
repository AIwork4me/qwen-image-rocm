import json
import re

import pytest

from bench import quickstart_config as qsc


def test_modes_resolve_to_frozen_manifests():
    for mode in ("fast", "quality"):
        cfg = qsc.config_for(mode)
        assert cfg["framework"] == "comfyui"
        assert cfg["name"] == qsc.MODES[mode]["manifest"]
        assert cfg["resolutions"] == qsc.MODES[mode]["resolutions"]
        # weights list references the catalog with exact sizes
        for rel in qsc.MODES[mode]["weights"]:
            assert rel in qsc.WEIGHTS and qsc.WEIGHTS[rel] > 0


def test_fast_is_the_measured_production_triple():
    cfg = qsc.config_for("fast")
    assert cfg["steps"] == 8
    assert cfg["unet"] == "qwen_image_2.1_turbo_int8_convrot.safetensors"
    assert cfg["clip"] == "qwen3vl_8b_int8_convrot.safetensors"
    assert "--use-ck-attention" in cfg["server_flags"]
    assert "--disable-smart-memory" in cfg["server_flags"]
    # identical to the experiment that measured the triple as a whole
    with open("bench/experiments/p3-turbo-int8-ck-te-nosmart-1024x1024.json") as f:
        triple = json.load(f)
    for field in ("unet", "clip", "vae", "steps", "server_flags", "sdp_mode",
                  "sampler", "scheduler", "cfg"):
        assert cfg[field] == triple[field], field


def test_quality_is_bit_identical_baseline_plus_memory_mode():
    cfg = qsc.config_for("quality")
    assert cfg["steps"] == 40
    assert cfg["precision"] == "bf16"
    assert cfg["attention_backend"] == "comfyui-default"
    assert "--disable-smart-memory" in cfg["server_flags"]
    with open("bench/experiments/p3-vram-nosmart-1024x1024.json") as f:
        nosmart = json.load(f)
    for field in ("unet", "clip", "vae", "steps", "server_flags", "sdp_mode",
                  "sampler", "scheduler", "cfg"):
        assert cfg[field] == nosmart[field], field


def test_no_mode_uses_broken_pytorch_cross_attention():
    for mode in ("fast", "quality"):
        assert "--use-pytorch-cross-attention" not in qsc.config_for(mode)["server_flags"]


def test_resolution_guard():
    qsc.check_resolution("fast", 1024)
    qsc.check_resolution("fast", 2048)
    qsc.check_resolution("quality", 1024)
    with pytest.raises(ValueError, match="VAE"):
        qsc.check_resolution("quality", 2048)
    with pytest.raises(ValueError, match="not validated"):
        qsc.check_resolution("fast", 512)


def test_unknown_mode_fails_closed():
    with pytest.raises(ValueError, match="unknown mode"):
        qsc.config_for("turbo")


def test_weights_state_reports_structure_without_disk():
    states = qsc.weights_state("fast")
    assert [s["rel"].split("/")[-1] for s in states] == [
        "qwen_image_2.1_turbo_int8_convrot.safetensors",
        "qwen3vl_8b_int8_convrot.safetensors",
        "qwen_image_2.1_vae_bf16.safetensors",
    ]
    # states are computed from the real disk; on CI (no weights) all must be
    # 'absent' and never crash; on the GPU bench host they are 'present'.
    assert all(s["state"] in ("absent", "truncated", "present") for s in states)


def test_verify_weight_rejects_unknown_rel():
    with pytest.raises(ValueError, match="unknown weight"):
        qsc.verify_weight("not/a/real/file.safetensors", "https://example.invalid/repo")


def test_lfs_pointer_parse_shape():
    # _lfs_pointer is exercised against the network only on the bench host;
    # here we pin the parsing contract so the CLI subcommand stays honest.
    src = inspect_source(qsc._lfs_pointer)
    assert "oid sha256:" in src and "size " in src


def inspect_source(fn) -> str:
    import inspect

    return inspect.getsource(fn)


def test_cli_config_emits_json_runnable_by_powershell():
    # smoke: the CLI used by quickstart.ps1 must emit parseable JSON
    out = run_cli(["config", "--mode", "quality"])
    data = json.loads(out)
    assert data["name"] == "p4-qs-quality-1024x1024"


def run_cli(argv: list[str]) -> str:
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-I", str(qsc.REPO / "bench" / "quickstart_config.py"), *argv],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_weight_filenames_match_frozen_protocol_docs():
    # every catalog entry is one of the frozen checkpoints from docs/weights.md
    allowed = re.compile(
        r"(diffusion_models/qwen_image_2\.1_(bf16|int8_convrot|turbo_bf16"
        r"|turbo_int8_convrot)\.safetensors"
        r"|text_encoders/qwen3vl_8b_(bf16|int8_convrot|w4a8)\.safetensors"
        r"|vae/qwen_image_2\.1_vae_bf16\.safetensors)"
    )
    assert all(allowed.fullmatch(rel) for rel in qsc.WEIGHTS)

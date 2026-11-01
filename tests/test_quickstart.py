import hashlib
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
        assert cfg["revision"] == qsc.WEIGHTS_REVISION
        # weights list references the catalog with exact sizes + pinned digests
        for rel in qsc.MODES[mode]["weights"]:
            assert rel in qsc.WEIGHTS and qsc.WEIGHTS[rel][0] > 0
            assert len(qsc.WEIGHTS[rel][1]) == 64


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
        qsc.verify_weight("not/a/real/file.safetensors")


# ---- P0-4: digest enforcement & failure injection ---------------------------

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def test_digest_table_complete_wellformed_and_distinct():
    assert len(qsc.WEIGHTS) == 8
    shas = set()
    for rel, (size, sha) in qsc.WEIGHTS.items():
        assert size > 0 and HEX64.fullmatch(sha), rel
        shas.add(sha)
    assert len(shas) == 8  # no copy-paste duplication in the trust anchor
    assert re.fullmatch(r"[0-9a-f]{40}", qsc.WEIGHTS_REVISION)


def _fake_weight_env(tmp_path, monkeypatch):
    """Isolate verify_weight on a tiny fake catalog entry (no 18 GB hashing)."""
    root = tmp_path / "ws"
    root.mkdir()
    monkeypatch.setattr(qsc, "WEIGHTS_ROOT", root)
    monkeypatch.setattr(qsc, "STAMP_PATH", tmp_path / "stamps.json")
    return root


def test_same_size_wrong_content_is_rejected(tmp_path, monkeypatch):
    root = _fake_weight_env(tmp_path, monkeypatch)
    good = hashlib.sha256(b"good-bytes-here").hexdigest()
    monkeypatch.setitem(qsc.WEIGHTS, "fake/x.safetensors", (15, good))
    (root / "fake").mkdir()
    (root / "fake" / "x.safetensors").write_bytes(b"evil-bytes-here")  # 15 bytes, wrong
    r = qsc.verify_weight("fake/x.safetensors")
    assert r["ok"] is False and r["reason"] == "digest-mismatch"
    assert r["local_sha256"] != r["expected_sha256"]


def test_correct_file_passes_then_stamp_caches(tmp_path, monkeypatch):
    root = _fake_weight_env(tmp_path, monkeypatch)
    data = b"good-bytes-here"
    monkeypatch.setitem(qsc.WEIGHTS, "fake/x.safetensors",
                        (len(data), hashlib.sha256(data).hexdigest()))
    (root / "fake").mkdir()
    f = root / "fake" / "x.safetensors"
    f.write_bytes(data)
    r1 = qsc.verify_weight("fake/x.safetensors")
    assert r1["ok"] is True and r1["reason"] == "hashed"
    r2 = qsc.verify_weight("fake/x.safetensors")
    assert r2["ok"] is True and r2["reason"] == "stamp-cache-hit"


def test_stamp_cache_cannot_mask_corruption(tmp_path, monkeypatch):
    """After a verified stamp, same-size corruption must still be caught:
    mtime changes with the bytes, so the cache key misses and we re-hash."""
    root = _fake_weight_env(tmp_path, monkeypatch)
    data = b"good-bytes-here"
    monkeypatch.setitem(qsc.WEIGHTS, "fake/x.safetensors",
                        (len(data), hashlib.sha256(data).hexdigest()))
    (root / "fake").mkdir()
    f = root / "fake" / "x.safetensors"
    f.write_bytes(data)
    assert qsc.verify_weight("fake/x.safetensors")["ok"] is True
    f.write_bytes(b"evil-bytes-here")  # same size, different bytes -> new mtime
    r = qsc.verify_weight("fake/x.safetensors")
    assert r["ok"] is False and r["reason"] == "digest-mismatch"


def test_truncated_and_absent_reported(tmp_path, monkeypatch):
    root = _fake_weight_env(tmp_path, monkeypatch)
    monkeypatch.setitem(qsc.WEIGHTS, "fake/x.safetensors",
                        (15, "0" * 64))
    (root / "fake").mkdir()
    (root / "fake" / "x.safetensors").write_bytes(b"short")
    assert qsc.verify_weight("fake/x.safetensors")["reason"] == "size-mismatch"
    monkeypatch.setitem(qsc.WEIGHTS, "fake/absent.safetensors", (15, "0" * 64))
    assert qsc.verify_weight("fake/absent.safetensors")["reason"] == "absent"


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

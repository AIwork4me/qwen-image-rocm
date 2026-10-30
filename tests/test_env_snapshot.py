import importlib.util
from datetime import datetime


def test_build_snapshot_fields():
    from tools.snapshot_env import build_snapshot

    d = build_snapshot(
        os_build="26300",
        gpu_name="AMD Radeon RX 7900 XTX",
        driver_version="32.0.21030.2001",
        python_version="3.12.0",
        torch_version=None,
        torchvision_version=None,
        hip_version=None,
        gfx_arch=None,
        created_at="2026-10-30T21:00:00+08:00",
    )
    assert set(d) == {
        "os_build",
        "gpu_name",
        "driver_version",
        "python_version",
        "torch_version",
        "torchvision_version",
        "hip_version",
        "gfx_arch",
        "created_at",
    }
    assert d["torch_version"] is None
    assert d["gpu_name"] == "AMD Radeon RX 7900 XTX"
    datetime.fromisoformat(d["created_at"])  # must parse as ISO 8601


def test_collect_without_torch(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.chdir(tmp_path)
    import tools.snapshot_env as se

    d = se.collect()
    assert d["torch_version"] is None
    assert d["torchvision_version"] is None
    assert d["hip_version"] is None
    assert d["gfx_arch"] is None
    # system fields still populated on a real machine
    assert len(d["python_version"]) > 0
    assert len(d["os_build"]) > 0
    assert "AMD" in d["gpu_name"] or len(d["gpu_name"]) > 0

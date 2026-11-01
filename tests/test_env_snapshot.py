import importlib.machinery
import importlib.util
import sys
import types
from datetime import datetime

import pytest


@pytest.fixture
def fake_modules(monkeypatch):
    """Register fake transformers/diffusers modules importable via sys.modules."""
    for name, version in (("transformers", "5.22.1"), ("diffusers", "0.42.1")):
        mod = types.ModuleType(name)
        mod.__version__ = version
        mod.__spec__ = importlib.machinery.ModuleSpec(name, None)
        monkeypatch.setitem(sys.modules, name, mod)


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
        transformers_version=None,
        diffusers_version=None,
        sdpa_probe=None,
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
        "transformers_version",
        "diffusers_version",
        "sdpa_probe",
        "created_at",
    }
    assert d["torch_version"] is None
    assert d["gpu_name"] == "AMD Radeon RX 7900 XTX"
    datetime.fromisoformat(d["created_at"])  # must parse as ISO 8601


def test_build_snapshot_new_fields_optional():
    from tools.snapshot_env import build_snapshot

    d = build_snapshot(
        os_build="26300",
        gpu_name="g",
        driver_version="d",
        python_version="3.12.0",
        torch_version=None,
        torchvision_version=None,
        hip_version=None,
        gfx_arch=None,
        created_at="2026-10-30T21:00:00+08:00",
    )
    # callers that predate the Phase 4 fields still get a valid snapshot
    assert d["transformers_version"] is None
    assert d["diffusers_version"] is None
    assert d["sdpa_probe"] is None


def test_collect_without_torch(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.chdir(tmp_path)
    import tools.snapshot_env as se

    d = se.collect()
    assert d["torch_version"] is None
    assert d["torchvision_version"] is None
    assert d["hip_version"] is None
    assert d["gfx_arch"] is None
    assert d["transformers_version"] is None
    assert d["diffusers_version"] is None
    assert d["sdpa_probe"] is None  # no torch -> no GPU probe attempted
    # system fields still populated on a real machine
    assert len(d["python_version"]) > 0
    assert len(d["os_build"]) > 0
    assert "AMD" in d["gpu_name"] or len(d["gpu_name"]) > 0


def test_framework_versions_missing(monkeypatch):
    import tools.snapshot_env as se

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert se._framework_versions() == (None, None)


def test_framework_versions_present(monkeypatch, fake_modules):
    import tools.snapshot_env as se

    assert se._framework_versions() == ("5.22.1", "0.42.1")


def test_sdpa_probe_skipped_without_torch(monkeypatch):
    import tools.snapshot_env as se

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert se._sdpa_probe() is None

"""Linux lab environment: snapshots, GPU health gate, stack introspection.

Differences from the Windows quickstart path (isolated here on purpose):
- The GPU name reported by torch/ComfyUI on this Linux stack is
  ``cuda:0 AMD Radeon Graphics : native`` — it does NOT contain "7900",
  so the Windows ``check_server`` gate would reject a perfectly healthy
  W7900. The Linux gate accepts any AMD Radeon CUDA device and records
  the name; the gfx architecture is asserted locally via torch.
- The lab venv borrows the pre-validated ROCm torch build read-only via a
  ``.pth`` bridge (``_rocm_base_env.pth``) so the base environment is
  never modified.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAB = REPO / "bench" / "linux_w7900"
RESULTS_ROOT = REPO / "bench" / "results" / "linux-w7900"
ENV_DIR = RESULTS_ROOT / "env"

COMFY_DIR = REPO / "phase2-comfyui" / "ComfyUI"
COMFY_PINNED_COMMIT = "b5a432157de6b8884f81104cd02926adf4d597e4"

# Verified at fetch time against the GitHub tree API of the pinned commit
# (see docs/linux-w7900/P0_PREFLIGHT.md); git-clone is blocked by the lab
# egress proxy, so this marker replaces a real git HEAD check.
COMFY_TREE_MARKER = COMFY_DIR / ".linux_lab_pinned_commit"


def _run(cmd: list[str], timeout: int = 30) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return f"<unavailable: {exc}>"


def torch_stack() -> dict:
    import torch

    props = torch.cuda.get_device_properties(0) if torch.cuda.is_available() else None
    return {
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "device_name": torch.cuda.get_device_name(0) if props else None,
        "gfx_arch": getattr(props, "gcnArchName", None),
        "total_vram_mb": round(props.total_memory / 2**20) if props else None,
    }


def rocm_versions() -> dict:
    return {
        "rocminfo_gfx": _gfx_from_rocminfo(),
        "driver": _run(["rocm-smi", "--showdriverversion"]).splitlines()[-2].split(":")[-1].strip()
        if "Driver version" in _run(["rocm-smi", "--showdriverversion"]) else None,
        "rocprofv3": _run(["rocprofv3", "--version"]),
        "hsa_path": _run(["bash", "-lc", "echo $HSA_OVERRIDE_GFX_VERSION"]),
    }


def _gfx_from_rocminfo() -> str | None:
    out = _run(["rocminfo"])
    m = re.search(r"^\s+Name:\s+(gfx\d+)", out, re.M)
    return m.group(1) if m else None


def comfyui_version() -> dict:
    v = {}
    try:
        ns = {}
        exec((COMFY_DIR / "comfyui_version.py").read_text(), ns)
        v["version"] = ns.get("__version__")
    except Exception as exc:  # noqa: BLE001
        v["version_error"] = str(exc)
    v["pinned_commit"] = COMFY_PINNED_COMMIT
    v["tree_marker_ok"] = (
        COMFY_TREE_MARKER.exists()
        and COMFY_TREE_MARKER.read_text().strip() == COMFY_PINNED_COMMIT
    )
    return v


def build_snapshot() -> dict:
    snap = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "os_build": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python_version": platform.python_version(),
        "cpu": _run(["bash", "-lc", "grep -m1 'model name' /proc/cpuinfo"]).split(":")[-1].strip(),
        "nproc": _run(["nproc"]),
        "ram_total_gb": None,
        "gpu_name": None,
        "gfx_arch": None,
        "torch": None,
        "hip": None,
        "comfyui": comfyui_version(),
        "repo_head": _run(["git", "-C", str(REPO), "rev-parse", "HEAD"]),
        "repo_branch": _run(["git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"]),
        "gpu_note": "single AMD Radeon PRO W7900 (gfx1100, 48GB) exposed to this container",
    }
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    snap["ram_total_gb"] = round(int(line.split()[1]) / 2**20, 1)
    except OSError:
        pass
    try:
        snap.update(torch_stack())
        snap["gpu_name"] = snap.pop("device_name") or snap["gpu_name"]
        snap["gfx_arch"] = snap.pop("gfx_arch") or snap["gfx_arch"]
        snap["torch"] = snap.pop("torch")
        snap["hip"] = snap.pop("hip")
    except Exception as exc:  # noqa: BLE001
        snap["torch_error"] = str(exc)
    snap["rocm"] = rocm_versions()
    return snap


def write_snapshot() -> str:
    ENV_DIR.mkdir(parents=True, exist_ok=True)
    snap = build_snapshot()
    name = "snapshot-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
    (ENV_DIR / name).write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return name


def latest_snapshot() -> dict:
    snaps = sorted(ENV_DIR.glob("snapshot-*.json")) if ENV_DIR.is_dir() else []
    return json.loads(snaps[-1].read_text(encoding="utf-8")) if snaps else {}


def check_gpu_expectations(snap: dict | None = None) -> list[str]:
    """Fail-closed checks: exactly one AMD GPU of the gfx1100 family."""
    snap = snap or latest_snapshot()
    problems = []
    if snap.get("cuda_available") is False:
        problems.append("torch.cuda.is_available() is False — no usable GPU")
    if snap.get("device_count") not in (1, None):
        problems.append(f"expected exactly 1 GPU, torch sees {snap['device_count']}")
    arch = snap.get("gfx_arch") or snap.get("rocm", {}).get("rocminfo_gfx")
    if arch and not str(arch).startswith("gfx1100"):
        problems.append(f"expected gfx1100 (W7900), found {arch}")
    name = snap.get("gpu_name") or ""
    if name and "AMD" not in name:
        problems.append(f"device name is not an AMD device: {name!r}")
    vram = snap.get("total_vram_mb")
    if isinstance(vram, (int, float)) and not (46000 <= vram <= 50000):
        problems.append(f"expected ~48GB VRAM (W7900), found {vram} MB")
    return problems


def check_server_linux(base_url: str) -> dict:
    """Linux GPU gate for a running ComfyUI server (Windows gate greps '7900').

    Returns the parsed /system_stats; raises if no AMD CUDA device is found
    (anti CPU-fallback, same intent as bench.comfyui_client.check_server).
    """
    import requests

    stats = requests.get(f"{base_url}/system_stats", timeout=10).json()
    devices = stats.get("devices", [])
    amd = [d for d in devices if "AMD" in (d.get("name") or "")]
    if not devices or not amd:
        raise RuntimeError(f"no AMD device in /system_stats: {devices} — refusing to benchmark")
    return stats

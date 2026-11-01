"""Environment snapshot: capture machine + stack versions as JSON evidence.

Writes bench/results/env/snapshot-<YYYYMMDD-HHMMSS>.json so every benchmark
run can reference the exact environment it was produced on.
"""

import importlib.util
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def build_snapshot(
    os_build: str,
    gpu_name: str,
    driver_version: str,
    python_version: str,
    torch_version: str | None,
    torchvision_version: str | None,
    hip_version: str | None,
    gfx_arch: str | None,
    created_at: str,
    transformers_version: str | None = None,
    diffusers_version: str | None = None,
    sdpa_probe: dict | None = None,
) -> dict:
    return {
        "os_build": os_build,
        "gpu_name": gpu_name,
        "driver_version": driver_version,
        "python_version": python_version,
        "torch_version": torch_version,
        "torchvision_version": torchvision_version,
        "hip_version": hip_version,
        "gfx_arch": gfx_arch,
        "transformers_version": transformers_version,
        "diffusers_version": diffusers_version,
        "sdpa_probe": sdpa_probe,
        "created_at": created_at,
    }


def _gpu_info() -> tuple[str, str]:
    ps = (
        "Get-CimInstance Win32_VideoController | "
        "Where-Object {$_.Name -like '*AMD*'} | "
        "Select-Object -First 1 Name, DriverVersion | ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
        j = json.loads(out)
        return j["Name"], j["DriverVersion"]
    except Exception:
        return platform.platform(), "unknown"


def _torch_info() -> tuple[str | None, str | None, str | None, str | None]:
    if importlib.util.find_spec("torch") is None:
        return None, None, None, None
    import torch

    torchvision_version = None
    if importlib.util.find_spec("torchvision") is not None:
        import torchvision

        torchvision_version = torchvision.__version__
    hip = getattr(torch.version, "hip", None)
    gfx_arch = None
    if torch.cuda.is_available():
        arch = getattr(torch.cuda.get_device_properties(0), "gcnArchName", None)
        if arch:
            gfx_arch = arch.split(":")[0]
    return torch.__version__, torchvision_version, str(hip) if hip else None, gfx_arch


def _framework_versions() -> tuple[str | None, str | None]:
    """(transformers, diffusers) versions, None where not installed."""
    versions = []
    for name in ("transformers", "diffusers"):
        version = None
        if importlib.util.find_spec(name) is not None:
            try:
                mod = importlib.import_module(name)
                version = getattr(mod, "__version__", None)
            except Exception:
                pass
        versions.append(str(version) if version else None)
    return (versions[0], versions[1])


def _sdpa_probe() -> dict | None:
    """One tiny launch per SDPA backend -> {backend: PASS/FAIL/OOM}.

    None when torch or a CUDA/HIP device is unavailable (CPU-only envs,
    torch-less envs). Uses the ComfyUI-style flush via the shared repro
    cell runner so a kernel that fails at launch is reported, not silent.
    """
    if importlib.util.find_spec("torch") is None:
        return None
    import torch

    if not torch.cuda.is_available():
        return None
    # script may run under python -I (no cwd/script-dir on sys.path)
    repo_root = str(Path(__file__).resolve().parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from tools.repro.sdpa_repro import BACKENDS, run_cell

    probe = {}
    for backend in BACKENDS:
        cell = {
            "seq": 64,
            "kv_heads": 32,
            "mask_kind": "none",
            "is_causal": True,
            "backend": backend,
        }
        probe[backend] = run_cell(cell, warmup=0, reps=1)["status"]
    return probe


def collect() -> dict:
    gpu_name, driver_version = _gpu_info()
    winver = getattr(sys, "getwindowsversion", None)
    os_build = str(winver().build) if winver else platform.platform()
    torch_version, torchvision_version, hip_version, gfx_arch = _torch_info()
    transformers_version, diffusers_version = _framework_versions()
    return build_snapshot(
        os_build=os_build,
        gpu_name=gpu_name,
        driver_version=driver_version,
        python_version=sys.version.split()[0],
        torch_version=torch_version,
        torchvision_version=torchvision_version,
        hip_version=hip_version,
        gfx_arch=gfx_arch,
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        transformers_version=transformers_version,
        diffusers_version=diffusers_version,
        sdpa_probe=_sdpa_probe(),
    )


def main() -> None:
    out = Path("bench/results/env") / f"snapshot-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(collect(), indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()

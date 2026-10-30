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


def collect() -> dict:
    gpu_name, driver_version = _gpu_info()
    winver = getattr(sys, "getwindowsversion", None)
    os_build = str(winver().build) if winver else platform.platform()
    torch_version, torchvision_version, hip_version, gfx_arch = _torch_info()
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
    )


def main() -> None:
    out = Path("bench/results/env") / f"snapshot-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(collect(), indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()

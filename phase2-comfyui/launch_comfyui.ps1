# Start the ComfyUI server for Phase 2 benchmarking.
# Usage: .\launch_comfyui.ps1 [-Port 8188] [-NoMath]   (-NoMath = default attention)
param(
    [int]$Port = 8188,
    [switch]$NoMath
)
# No $ErrorActionPreference='Stop': PS5.1 turns native stderr progress into
# terminating errors (Phase-1 lesson).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "ComfyUI")
if (-not $NoMath) { $env:QIR_SDP = "math" } else { Remove-Item Env:QIR_SDP -ErrorAction SilentlyContinue }
& (Join-Path $here ".venv\Scripts\python.exe") (Join-Path $here "launch_wrapper.py") `
    --listen 127.0.0.1 --port $Port --extra-model-paths-config (Join-Path $here "extra_model_paths.yaml")

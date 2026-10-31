# Start the ComfyUI server for Phase 2/3 benchmarking.
# Usage:
#   .\launch_comfyui.ps1 [-Port 8188] [-NoMath] [-SdpMode math|none|math-hard] [-ComfyArgs "--flag --flag2"]
# -NoMath = default attention (same as -SdpMode none; kept for Phase 2 compat)
# -SdpMode math-hard = math workaround + block ComfyUI's own SDPA re-enable
#   (needed with --use-pytorch-cross-attention; see launch_wrapper.py)
param(
    [int]$Port = 8188,
    [switch]$NoMath,
    [string]$SdpMode = "",
    [string]$ComfyArgs = ""
)
# No $ErrorActionPreference='Stop': PS5.1 turns native stderr progress into
# terminating errors (Phase-1 lesson).
if (-not $SdpMode) { if ($NoMath) { $SdpMode = "none" } else { $SdpMode = "math" } }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "ComfyUI")
if ($SdpMode -eq "none") {
    Remove-Item Env:QIR_SDP -ErrorAction SilentlyContinue
} else {
    $env:QIR_SDP = $SdpMode
}
$py = Join-Path $here ".venv\Scripts\python.exe"
$allArgs = @(
    (Join-Path $here "launch_wrapper.py"),
    "--listen", "127.0.0.1", "--port", "$Port",
    "--extra-model-paths-config", (Join-Path $here "extra_model_paths.yaml")
)
if ($ComfyArgs) { $allArgs += ($ComfyArgs -split " ") | Where-Object { $_ } }
Write-Host "launching: QIR_SDP=$SdpMode python $($allArgs -join ' ')"
& $py @allArgs

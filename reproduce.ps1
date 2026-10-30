# qwen-image-rocm reproduction entrypoint ("stranger standard": a fresh
# machine with a 7900 XTX should reproduce our numbers in ~30 minutes).
#
# Usage:
#   .\reproduce.ps1 -Quick   # one config: p2-en-scene, 1024x1024, 40 steps, seed 42
#   .\reproduce.ps1 -Full    # the whole Phase 1 protocol (~1.5-3 h + GPU)
#
# Idempotent: skips an existing venv and existing weights.

param(
    [switch]$Quick,
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

if (-not ($Quick -or $Full)) {
    Write-Host "Choose one: -Quick (single config) or -Full (whole protocol)"
    exit 1
}

# --- uv check ------------------------------------------------------------
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    $uvPath = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe"
    if (Test-Path $uvPath) { $uv = $uvPath } else {
        Write-Host "uv not found. Install it first: winget install --id=astral-sh.uv -e"
        exit 1
    }
} else { $uv = $uv.Source }

# --- venv (skip if it exists) ---------------------------------------------
$venvDir = Join-Path $repo ".venv-repro"
$py = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "[1/4] creating venv (.venv-repro, Python 3.12)..."
    & $uv venv $venvDir --python 3.12 --seed
    if ($LASTEXITCODE -ne 0) { exit 1 }

    Write-Host "[2/4] installing AMD ROCm torch stack (mandated command)..."
    & $py -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1100]==2.12.0+rocm7.14.1" "torchvision[device-gfx1100]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"
    if ($LASTEXITCODE -ne 0) { exit 1 }
    & $py -c "import torch; assert torch.__version__.endswith('rocm7.14.1'), torch.__version__; print('torch OK', torch.__version__)"
    if ($LASTEXITCODE -ne 0) { Write-Host "torch build check failed"; exit 1 }

    & $py -m pip install -r (Join-Path $repo "phase1-diffusers\requirements.txt")
    if ($LASTEXITCODE -ne 0) { exit 1 }
    & $py -c "import torch; assert torch.__version__.endswith('rocm7.14.1'), torch.__version__; print('torch still OK', torch.__version__)"
    if ($LASTEXITCODE -ne 0) { Write-Host "pip swapped the ROCm torch for a PyPI build"; exit 1 }
} else {
    Write-Host "[1-2/4] reusing existing .venv-repro"
}

# --- HIP smoke ------------------------------------------------------------
Write-Host "[3/4] HIP smoke test..."
& $py -I (Join-Path $repo "phase1-diffusers\smoke_hip.py")
if ($LASTEXITCODE -ne 0) { Write-Host "HIP smoke failed - see output above"; exit 1 }

# --- weights (skip if present) --------------------------------------------
$weights = Join-Path $repo "weights\diffusers-format"
$modelIndex = Join-Path $weights "model_index.json"
if (-not (Test-Path $modelIndex)) {
    Write-Host "[4/4] downloading weights from ModelScope (~30 GB, first run only)..."
    & (Join-Path $venvDir "Scripts\modelscope.exe") download --model Qwen/Qwen-Image-2.1 --local_dir $weights
    if ($LASTEXITCODE -ne 0) { exit 1 }
} else {
    Write-Host "[4/4] weights already present"
}

# --- run -------------------------------------------------------------------
# Required on this stack (torch 2.12.0+rocm7.14.1 Windows gfx1100): the flash
# and mem-efficient SDPA backends fail with hipErrorInvalidValue — see
# docs/issues/2026-10-30-hiperrorinvalidvalue-qwen3vl-textencoder.md
$env:QIR_SDP = "math"

if ($Quick) {
    $t = Get-Date
    & $py -I (Join-Path $repo "phase1-diffusers\generate.py") `
        --prompt-id p2-en-scene --width 1024 --height 1024 --steps 40 --seed 42 `
        --out (Join-Path $repo "results\raw\repro")
    if ($LASTEXITCODE -ne 0) { exit 1 }
    Write-Host ("Quick reproduction finished in {0:N1} minutes (incl. model load). Compare wall time with results/raw/repro/... JSON." -f ((Get-Date) - $t).TotalMinutes)
} else {
    $date = Get-Date -Format "yyyy-MM-dd"
    # 2048 is blocked on every working backend (32.1 GB dense attention
    # allocation > 24 GB VRAM) — see the SDPA issue doc above.
    & $py -I (Join-Path $repo "bench\run_bench.py") --date $date --resolutions 1024
    if ($LASTEXITCODE -ne 0) { exit 1 }
    & $py -I (Join-Path $repo "bench\make_report.py") (Join-Path $repo "bench\results\$date")
    Write-Host "Full protocol done. Report: bench\results\$date\report.md"
}

# qwen-image-rocm quickstart - the one-command path to a first real image.
#
#   .\quickstart.ps1 -Mode Fast       # ~8-9 s/image @1024 (turbo int8 + ck)
#   .\quickstart.ps1 -Mode Quality    # bf16-40, bit-identical baseline
#   .\quickstart.ps1 -Mode Fast -Resolution 2048
#
# Both modes map to frozen, measured experiment manifests (see
# bench/quickstart_config.py - single source of truth). The script:
#   checks Windows 11 / Radeon GPU / gfx1100 -> provisions an isolated venv
#   with the pinned AMD ROCm wheels -> clones ComfyUI at the pinned commit
#   -> verifies weights (exact size + authoritative LFS sha256 when
#   downloaded here) -> starts the server (port-safe, own process tree only)
#   -> runs a smoke generation through the same driver as the benchmarks
#   -> prints image paths + cold/warm timings. No silent CPU fallback:
#   the health gate requires a Radeon device from the server itself.
#
# Safe to re-run: every step is idempotent; downloads resume per-chunk
# (tools/download_parallel.py). PowerShell 5.1 and 7 compatible.
#
# Switches:
#   -SkipSetup        assume venv + ComfyUI + weights already provisioned
#   -KeepServer       leave the ComfyUI server running afterwards
#   -AllowUntestedGpu proceed on a Radeon that is not the RX 7900 XTX
#                     (project numbers are verified on 7900 XTX only)
#   -Prompt           p1-zh-scene | p2-en-scene | p3-poster-text
#   -Port             base port (auto-falls forward if busy; never kills
#                     a process this script did not start)

param(
    [ValidateSet("Fast", "Quality")][string]$Mode = "Fast",
    [int]$Resolution = 1024,
    [string]$Prompt = "p2-en-scene",
    [int]$Port = 8188,
    [switch]$SkipSetup,
    [switch]$KeepServer,
    [switch]$AllowUntestedGpu,
    [int]$HealthTimeoutS = 900
)

# NOTE: no $ErrorActionPreference = "Stop" - under Windows PowerShell 5.1
# that turns native stderr progress output (uv/pip/git) into terminating
# errors. Every native call below checks $LASTEXITCODE explicitly instead.
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo
$ComfyCommit = "b5a432157de6b8884f81104cd02926adf4d597e4"   # pinned (setup.md)
$TorchPin = "2.12.0+rocm7.14.1"                             # verified baseline
$HfBaseDefault = "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1"

function Fail([string]$what, [string]$why, [string]$fix) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Red
    Write-Host "QUICKSTART FAILED: $what" -ForegroundColor Red
    Write-Host "why : $why"
    Write-Host "fix : $fix"
    Write-Host "=========================================================" -ForegroundColor Red
    if (-not $KeepServer -and $server -and -not $server.HasExited) {
        taskkill /PID $server.Id /T /F 2>$null | Out-Null
    }
    exit 1
}

Write-Host "== qwen-image-rocm quickstart == mode=$Mode resolution=${Resolution}x${Resolution} prompt=$Prompt"

# --- 1. Windows 11 check ----------------------------------------------------
$build = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuildNumber
if ([int]$build -lt 22000) {
    Fail "unsupported Windows" "Windows build $build (< 22000); this project verifies Windows 11 native ROCm only" "upgrade to Windows 11, or run the Linux ROCm stack (not covered by this repo)"
}
Write-Host "[ok] Windows 11 (build $build)"

# --- 2. GPU pre-check (before any install) ----------------------------------
$gpus = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match "Radeon" }
if (-not $gpus) {
    Fail "no AMD Radeon GPU found" "this project runs on Radeon GPUs via native Windows ROCm" "check the GPU is present and the Adrenalin driver is installed"
}
$gpu = $gpus | Where-Object { $_.Name -match "7900 XTX" } | Select-Object -First 1
if ($gpu) {
    Write-Host "[ok] AMD $($gpu.Name) (driver $($gpu.DriverVersion))"
} elseif ($AllowUntestedGpu) {
    $gpu = $gpus | Select-Object -First 1
    Write-Warning "AMD $($gpu.Name) is NOT a verified GPU (project numbers: RX 7900 XTX / gfx1100 only); continuing because -AllowUntestedGpu was given"
} else {
    Fail "untested GPU" "found AMD $($gpus[0].Name); all published numbers are measured on Radeon RX 7900 XTX (gfx1100)" "rerun with -AllowUntestedGpu to try it anyway, or use a 7900 XTX"
}

# --- 3. uv -------------------------------------------------------------------
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    $uvPath = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe"
    if (Test-Path $uvPath) { $uv = $uvPath } else {
        Fail "uv not found" "uv provisions the isolated python environment" "winget install --id=astral-sh.uv -e"
    }
} else { $uv = $uv.Source }
Write-Host "[ok] uv: $uv"

# --- 4. mode config (single source of truth: bench/quickstart_config.py) -----
$cfgJson = & $uv run --python 3.12 --with requests --with jsonschema python -I (Join-Path $repo "bench\quickstart_config.py") config --mode $Mode 2>$null
if ($LASTEXITCODE -ne 0) { Fail "invalid mode/config" "quickstart_config.py rejected mode '$Mode'" "use -Mode Fast or -Mode Quality" }
# join stdout lines before parsing: PS 5.1 pipes a string ARRAY line-by-line
# into ConvertFrom-Json, silently producing broken objects otherwise
$cfg = ($cfgJson -join "`n") | ConvertFrom-Json
if ($cfg.resolutions -notcontains $Resolution) {
    if ($Mode -eq "Quality" -and $Resolution -eq 2048) {
        Fail "Quality mode does not support 2048" "bf16 VAE decode allocates a 20.25 GB tensor and OOMs on 24 GB cards (docs/issues/evidence/sdpa-7140-2048-vae-oom.log)" "use -Mode Fast -Resolution 2048 (turbo int8 route, measured)"
    }
    Fail "unsupported resolution" "resolution ${Resolution} not validated for mode $Mode (tested: $($cfg.resolutions -join ', '))" "use 1024 (both modes) or 2048 (Fast)"
}
$manifestName = $cfg.name
$venvDir = Join-Path $repo "phase2-comfyui\.venv"
$py = Join-Path $venvDir "Scripts\python.exe"
$comfyDir = Join-Path $repo "phase2-comfyui\ComfyUI"
Write-Host "[ok] profile: $manifestName (steps=$($cfg.steps), attention=$($cfg.attention_backend), flags=$($cfg.server_flags -join ' '))"

# --- 5. isolated venv + pinned AMD ROCm wheels -------------------------------
if (-not $SkipSetup) {
    $haveTorch = $false
    if (Test-Path $py) {
        & $py -c "import torch" 2>$null
        if ($LASTEXITCODE -eq 0) { $haveTorch = $true }
    }
    if (-not $haveTorch) {
        Write-Host "[1/6] creating isolated venv ($venvDir)..."
        if (Test-Path $venvDir) { Remove-Item -Recurse -Force $venvDir }   # partial venv breaks uv venv
        & $uv venv $venvDir --python 3.12 --seed
        if ($LASTEXITCODE -ne 0) { Fail "venv creation failed" "uv venv exited $LASTEXITCODE" "see output above" }
        Write-Host "[2/6] installing pinned AMD ROCm torch ($TorchPin) from repo.amd.com..."
        & $py -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1100]==$TorchPin" "torchvision[device-gfx1100]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"
        if ($LASTEXITCODE -ne 0) { Fail "AMD wheel install failed" "pip exited $LASTEXITCODE (network or index issue?)" "retry - the command is resumable; see docs/weights.md network notes for mainland mirrors" }
    } else {
        Write-Host "[1-2/6] reusing existing venv (torch imports)"
    }

    # --- 6. ComfyUI at the pinned commit ---------------------------------------
    if (-not (Test-Path (Join-Path $comfyDir "main.py"))) {
        Write-Host "[3/6] cloning ComfyUI @ $ComfyCommit (depth 1)..."
        New-Item -ItemType Directory -Force -Path $comfyDir | Out-Null
        git -C $comfyDir init 2>$null | Out-Null
        git -C $comfyDir remote add origin https://github.com/comfyanonymous/ComfyUI.git 2>$null | Out-Null
        git -C $comfyDir fetch --depth 1 origin $ComfyCommit
        if ($LASTEXITCODE -ne 0) { Fail "ComfyUI fetch failed" "git fetch exited $LASTEXITCODE" "check network access to github.com, then rerun (resumable)" }
        git -C $comfyDir -c advice.detachedHead=false checkout FETCH_HEAD
        if ($LASTEXITCODE -ne 0) { Fail "ComfyUI checkout failed" "git checkout exited $LASTEXITCODE" "see output above" }
    } else {
        $head = git -C $comfyDir rev-parse HEAD 2>$null
        if ("$head" -ne $ComfyCommit) {
            Write-Warning "ComfyUI checkout is at $head, pinned commit is $ComfyCommit - keeping yours (delete phase2-comfyui/ComfyUI to re-pin)"
        }
    }
    & $py -m pip install -r (Join-Path $comfyDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "ComfyUI requirements failed" "pip exited $LASTEXITCODE" "see output above" }
    & $py -m pip install requests websocket-client jsonschema
    if ($LASTEXITCODE -ne 0) { Fail "driver deps failed" "pip exited $LASTEXITCODE" "see output above" }
    & $py -c "import torch; assert torch.__version__.endswith('rocm7.14.1'), torch.__version__; print('[ok] torch', torch.__version__)"
    if ($LASTEXITCODE -ne 0) { Fail "torch build check failed" "a later pip install swapped the ROCm torch for a PyPI build" "rerun with a fresh venv (delete $venvDir)" }
} else {
    if (-not (Test-Path $py)) { Fail "-SkipSetup but no venv" "$py not found" "rerun without -SkipSetup" }
    Write-Host "[setup skipped] using existing environment"
}

# --- 7. gfx1100 assertion (no silent CPU / wrong-arch fallback) ---------------
& $py -c "import torch; d=torch.cuda.is_available(); assert d, 'no HIP device'; n=torch.cuda.get_device_name(0); c=torch.cuda.get_device_capability(0); assert c==(11,0), f'gfx{c[0]}{c[1]} not gfx1100'; print('[ok]', n, 'gfx1100, HIP', torch.version.hip)"
if ($LASTEXITCODE -ne 0) {
    Fail "gfx1100 check failed" "torch cannot see a gfx1100 HIP device (output above)" "install/repair the Adrenalin driver; this script never falls back to CPU"
}

# --- 8. weights: check -> (resumable) download -> integrity -------------------
$hfBase = if ($env:HF_ENDPOINT) { "$($env:HF_ENDPOINT.TrimEnd('/'))/Comfy-Org/Qwen-Image-2.1" } else { $HfBaseDefault }
Write-Host "[4/6] weights (source: Comfy-Org/Qwen-Image-2.1 via $hfBase)..."
$wsJson = & $py -I (Join-Path $repo "bench\quickstart_config.py") weights-state --mode $Mode 2>$null
if ($LASTEXITCODE -ne 0) { Fail "weights-state failed" "python exited $LASTEXITCODE" "see output above" }
$need = @((($wsJson -join "`n") | ConvertFrom-Json))
if (-not $need -or -not $need[0].rel) { Fail "weights-state parse failed" "could not parse quickstart_config.py output" "run: python -I bench\quickstart_config.py weights-state --mode $Mode" }
foreach ($w in $need) {
    if ($w.state -eq "present") { Write-Host "[ok] $($w.rel) ($([math]::Round($w.expected_bytes/1GB,2)) GB)"; continue }
    if ($SkipSetup) { Fail "-SkipSetup but weights incomplete" "$($w.rel) is $($w.state)" "rerun without -SkipSetup to download (resumable), or place the file at weights\comfyui-split\$($w.rel)" }
    Write-Host "[download] $($w.rel) ($([math]::Round($w.expected_bytes/1GB,2)) GB) - resumable, safe to Ctrl+C and rerun"
    $dest = Join-Path $repo (Join-Path "weights\comfyui-split" $w.rel)
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    & $py -I (Join-Path $repo "tools\download_parallel.py") "$hfBase/resolve/main/$($w.rel)" $dest 16
    if ($LASTEXITCODE -ne 0) { Fail "download failed" "tools/download_parallel.py exited $LASTEXITCODE for $($w.rel)" "rerun the same command - chunks resume byte-exact" }
    $vJson = & $py -I (Join-Path $repo "bench\quickstart_config.py") verify-weight --rel $w.rel --url-base $hfBase
    if ($LASTEXITCODE -ne 0) { Fail "integrity check crashed" "verify-weight exited $LASTEXITCODE" "network reachability of $hfBase/raw endpoints; then rerun" }
    $v = ($vJson -join "`n") | ConvertFrom-Json
    if (-not $v.ok) {
        & $py -I (Join-Path $repo "tools\download_parallel.py") "$hfBase/resolve/main/$($w.rel)" $dest 16
        $vJson = & $py -I (Join-Path $repo "bench\quickstart_config.py") verify-weight --rel $w.rel --url-base $hfBase
        $v = ($vJson -join "`n") | ConvertFrom-Json
    }
    if (-not $v.ok) { Fail "weight integrity mismatch" "$($w.rel): sha256/size does not match the host's LFS pointer" "delete the file and rerun to re-download" }
    Write-Host "[ok] $($w.rel) verified (sha256 matches $hfBase LFS pointer)"
}

# --- 9. start server (port-safe: own orphans only, spare-port fallback) -------
function Test-PortBusy([int]$p) {
    [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}
function Kill-OwnOrphans([int]$p) {
    foreach ($c in @(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)) {
        if ($c.OwningProcess -le 0) { continue }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)" -ErrorAction SilentlyContinue
        if ("$($proc.CommandLine)" -match "phase2-comfyui") {
            Write-Host "killing orphaned server PID $($c.OwningProcess) on port $p (this repo's leftover)"
            taskkill /PID $c.OwningProcess /T /F 2>$null | Out-Null
        }
    }
    Start-Sleep 2
}
Kill-OwnOrphans $Port
$origPort = $Port
while (Test-PortBusy $Port) {
    Write-Warning "port $Port busy (not ours) - trying next"
    $Port++
    if ($Port -gt ($origPort + 20)) { Fail "no free port" "ports $origPort..$($origPort+20) all busy" "free a port or pass -Port <n>" }
}

Write-Host "[5/6] starting ComfyUI (sdp=$($cfg.sdp_mode) flags=$($cfg.server_flags -join ' ')) on port $Port..."
$tServerStart = Get-Date
$resultsDir = Join-Path $repo "bench\results\quickstart-$Mode-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null   # must exist before Start-Process redirects logs into it
$launch = Join-Path $repo "phase2-comfyui\launch_comfyui.ps1"
$flagStr = $cfg.server_flags -join " "
$argStr = "-NoProfile -ExecutionPolicy Bypass -File `"$launch`" -Port $Port -SdpMode $($cfg.sdp_mode)"
if ($flagStr) { $argStr += " -ComfyArgs `"$flagStr`"" }
$server = Start-Process -FilePath "powershell" -ArgumentList $argStr -PassThru `
    -RedirectStandardOutput (Join-Path $resultsDir "server.log") -RedirectStandardError (Join-Path $resultsDir "server.err.log") `
    -WindowStyle Hidden
if (-not $server -or $server.Id -le 0) { Fail "server start failed" "Start-Process returned no process" "check powershell availability" }

$deadline = (Get-Date).AddSeconds($HealthTimeoutS)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep 3
    if ($server.HasExited) { break }
    try {
        $stats = Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 5
        $dev = $stats.devices | Where-Object { $_.name -match "Radeon" } | Select-Object -First 1
        if ($dev) { $healthy = $true; $tHealthy = Get-Date; break }
    } catch { }
}
if (-not $healthy) {
    $tail = @()
    foreach ($f in @("server.log", "server.err.log")) {
        $p = Join-Path $resultsDir $f
        if (Test-Path $p) { $tail += Get-Content $p -Tail 25 }
    }
    Fail "server health gate failed" "no Radeon device reported by /system_stats within ${HealthTimeoutS}s (server may have crashed - tail below)`n$($tail -join "`n")" "read the log tail above; common causes: driver/ROCm install, weights path (weights\comfyui-split), port conflict"
}
$bootS = [math]::Round(($tHealthy - $tServerStart).TotalSeconds, 1)
Write-Host "[ok] server healthy in ${bootS}s - GPU: $($dev.name) (VRAM $([math]::Round($dev.vram_total/1GB,1)) GB)"

# --- 10. smoke generation through the benchmark driver ------------------------
Write-Host "[6/6] generating (cold + warm) via the benchmark driver..."
$driverArgs = @("run", "--python", "3.12", "--with", "requests", "--with", "websocket-client", "--with", "jsonschema",
    "python", "-I", (Join-Path $repo "bench\run_comfyui.py"),
    "--date", (Split-Path -Leaf $resultsDir),
    "--experiment", $manifestName,
    "--base-url", "http://127.0.0.1:$Port",
    "--only-prompt", $Prompt, "--measured", "2", "--session", "quickstart")
if ($Resolution -ne $cfg.resolution) { $driverArgs += @("--resolution", "$Resolution") }
& $uv @driverArgs
$driverCode = $LASTEXITCODE
if ($driverCode -ne 0) {
    Fail "generation failed" "bench/run_comfyui.py exited $driverCode" "see driver output above; check server logs in $resultsDir"
}

# --- 11. report ----------------------------------------------------------------
$records = Get-ChildItem $resultsDir -Filter *.json | ForEach-Object { Get-Content $_.FullName -Raw | ConvertFrom-Json }
$cold = $records | Where-Object { $_.run_kind -eq "cold" } | Select-Object -First 1
$measures = @($records | Where-Object { $_.run_kind -eq "measure" })
$warmMed = if ($measures) { [math]::Round(($measures | ForEach-Object { $_.runs[0].total_s } | Measure-Object -Average).Average, 2) } else { 0 }
$tDone = Get-Date
$wallS = [math]::Round(($tDone - $tServerStart).TotalSeconds, 1)
$imgs = Get-ChildItem (Join-Path $repo (Join-Path "results\raw" (Split-Path -Leaf $resultsDir))) -Filter *.png -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "==================== quickstart done ====================" -ForegroundColor Green
Write-Host ("mode={0}  resolution={1}  steps={2}  prompt={3}" -f $Mode, $Resolution, $cfg.steps, $Prompt)
Write-Host ("GPU: {0}   torch: {1}" -f $dev.name, $TorchPin)
Write-Host ("server boot (start -> healthy):     {0} s" -f $bootS)
if ($cold) { Write-Host ("cold image (server up -> 1st png, incl. model load): {0} s  [text-encode {1} s, denoise {2} s, vae {3} s]" -f [math]::Round($cold.runs[0].total_s,1), [math]::Round($cold.runs[0].text_encode_s,2), [math]::Round($cold.runs[0].denoise_s,2), [math]::Round($cold.runs[0].vae_decode_s,2)) }
Write-Host ("warm steady state (avg of {0}):     {1} s/image  [same prompt, text-encode cached]" -f $measures.Count, $warmMed)
Write-Host ("total wall clock this run:          {0} s" -f $wallS)
if ($imgs) {
    Write-Host "images:" -ForegroundColor Green
    $imgs | ForEach-Object { Write-Host "  $($_.FullName)" }
}
Write-Host ("records: {0}" -f $resultsDir)
Write-Host "note: fresh-prompt cost = warm + a real text-encode (~1.2 s int8 / 3-7 s bf16);"
Write-Host "      first-ever run adds one-time weight download (~18 GB Fast / ~32 GB Quality)."
Write-Host "=========================================================" -ForegroundColor Green

# --- 12. teardown (own process tree only) --------------------------------------
if ($KeepServer) {
    Write-Host "server left running: http://127.0.0.1:$Port (PID $($server.Id); stop with: taskkill /PID $($server.Id) /T /F)"
} else {
    if (-not $server.HasExited) { taskkill /PID $server.Id /T /F 2>$null | Out-Null }
    Start-Sleep 2
    Kill-OwnOrphans $Port
    Write-Host "server stopped"
}
exit 0

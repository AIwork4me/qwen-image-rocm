# qwen-image-rocm quickstart - the one-command path to a first real image.
#
#   .\quickstart.ps1 -Mode Fast       # ~8-9 s/image warm @1024 (turbo int8 + ck)
#   .\quickstart.ps1 -Mode Quality    # bf16-40, bit-identical baseline
#   .\quickstart.ps1 -Mode Fast -Resolution 2048
#
# Both modes map to frozen experiment manifests (bench/quickstart_config.py
# - single source of truth). Chain: Windows11 / Radeon / gfx1100 checks ->
# isolated venv with pinned AMD ROCm wheels -> ComfyUI at the pinned commit
# (a mismatched commit FAILS CLOSED unless -AllowComfyCommitDrift, and a
# drift run is recorded as an unverified stack) -> weight integrity: exact
# size + pinned-revision SHA256 for EVERY file, freshly downloaded or not
# (fast re-checks via a stamp cache) -> server health gate that REQUIRES a
# Radeon device (no silent CPU fallback) -> generation via the benchmark
# driver -> a timing report using the unified cold-start vocabulary:
#   Server boot / Ready-to-first-image / Full cold start / Warm mean+median.
#
# Process ownership (bench/portops.ps1): a busy port is never taken from
# its listener (fall forward to a free port); teardown kills ONLY the tree
# this run started (tracked by PID, never by name matching). -KeepServer
# leaves it running and prints the exact PIDs + stop command.
#
# Results isolation: run records/images land under bench\results\quickstart\
# and results\raw\quickstart\ (gitignored) - a local run never dirties the
# git worktree; publish evidence explicitly with `git add -f` if ever needed.
# Safe to re-run: every step idempotent; downloads resume per-chunk.
# PowerShell 5.1 and 7 compatible.
#
# Switches:
#   -Mode Fast|Quality         generation profile (frozen manifests)
#   -Resolution 1024|2048      (2048 = Fast only; Quality VAE OOMs)
#   -Prompt p1-zh-scene|p2-en-scene|p3-poster-text
#   -Port <n>                  preferred port; falls forward if busy
#   -SkipSetup                 skip INSTALLS, still VERIFY the stack
#                               (torch pin, ComfyUI commit, weight digests)
#   -AllowComfyCommitDrift     experimental: proceed on a ComfyUI checkout at
#                              a different commit; run recorded as UNVERIFIED
#   -AllowUntestedGpu          proceed on a non-7900-XTX Radeon
#   -KeepServer                leave the server running (PIDs printed)

param(
    [ValidateSet("Fast", "Quality")][string]$Mode = "Fast",
    [int]$Resolution = 1024,
    [string]$Prompt = "p2-en-scene",
    [int]$Port = 8188,
    [switch]$SkipSetup,
    [switch]$KeepServer,
    [switch]$AllowUntestedGpu,
    [switch]$AllowComfyCommitDrift,
    [int]$HealthTimeoutS = 900
)

# NOTE: no $ErrorActionPreference = "Stop" - under Windows PowerShell 5.1
# that turns native stderr progress output (uv/pip/git) into terminating
# errors. Every native call below checks $LASTEXITCODE explicitly instead.
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo
. (Join-Path $repo "bench\portops.ps1")
$ComfyCommit = "b5a432157de6b8884f81104cd02926adf4d597e4"   # pinned (setup.md)
$TorchPin = "2.12.0+rocm7.14.1"                             # verified baseline
$HfBaseDefault = "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1"
$script:OwnPids = @()
$script:ServerProc = $null
$StackVerified = $true

function Fail([string]$what, [string]$why, [string]$fix) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Red
    Write-Host "QUICKSTART FAILED: $what" -ForegroundColor Red
    Write-Host "why : $why"
    Write-Host "fix : $fix"
    Write-Host "=========================================================" -ForegroundColor Red
    if (-not $KeepServer -and $script:ServerProc -and -not $script:ServerProc.HasExited) {
        Stop-OwnTree $script:ServerProc.Id $script:OwnPids $Port
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
    }
    & $py -m pip install -r (Join-Path $comfyDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "ComfyUI requirements failed" "pip exited $LASTEXITCODE" "see output above" }
    & $py -m pip install requests websocket-client jsonschema
    if ($LASTEXITCODE -ne 0) { Fail "driver deps failed" "pip exited $LASTEXITCODE" "see output above" }
} else {
    if (-not (Test-Path $py)) { Fail "-SkipSetup but no venv" "$py not found" "rerun without -SkipSetup" }
    Write-Host "[setup skipped] installs skipped - stack verification still enforced"
}

# --- 7. STACK VERIFICATION (always, incl. -SkipSetup; review P0-5) -----------
# torch build pin (also catches a PyPI swap)
& $py -c "import torch; assert torch.__version__.endswith('rocm7.14.1'), torch.__version__; print('[ok] torch', torch.__version__)"
if ($LASTEXITCODE -ne 0) {
    Fail "torch build check failed" "venv torch is not $TorchPin (PyPI swap or wrong venv)" "recreate the venv: delete $venvDir and rerun without -SkipSetup"
}
# ComfyUI commit pin - fail closed on drift unless explicitly overridden
$headCommit = git -C $comfyDir rev-parse HEAD 2>$null
if ("$headCommit" -ne $ComfyCommit) {
    if ($AllowComfyCommitDrift) {
        $StackVerified = $false
        Write-Warning "EXPERIMENTAL / UNVERIFIED STACK: ComfyUI is at $headCommit, pinned verified commit is $ComfyCommit - continuing because -AllowComfyCommitDrift was given; this run is recorded as stack_verified=false"
    } else {
        Fail "ComfyUI commit mismatch (fail closed)" "checkout is at $headCommit; every published number was measured at $ComfyCommit" "git -C phase2-comfyui\ComfyUI fetch --depth 1 origin $ComfyCommit; git -C phase2-comfyui\ComfyUI checkout FETCH_HEAD - or rerun with -AllowComfyCommitDrift to run EXPERIMENTAL (recorded unverified)"
    }
} else {
    Write-Host "[ok] ComfyUI @ $headCommit (pinned)"
}
# gfx1100 assertion (no silent CPU / wrong-arch fallback)
& $py -c "import torch; d=torch.cuda.is_available(); assert d, 'no HIP device'; n=torch.cuda.get_device_name(0); c=torch.cuda.get_device_capability(0); assert c==(11,0), f'gfx{c[0]}{c[1]} not gfx1100'; print('[ok]', n, 'gfx1100, HIP', torch.version.hip)"
if ($LASTEXITCODE -ne 0) {
    Fail "gfx1100 check failed" "torch cannot see a gfx1100 HIP device (output above)" "install/repair the Adrenalin driver; this script never falls back to CPU"
}

# --- 8. weights: size -> (resumable) download -> pinned-digest SHA256 --------
$hfBase = if ($env:HF_ENDPOINT) { "$($env:HF_ENDPOINT.TrimEnd('/'))/Comfy-Org/Qwen-Image-2.1" } else { $HfBaseDefault }
Write-Host "[4/6] weights (pinned revision, sha256-enforced for ALL files)..."
$wsJson = & $py -I (Join-Path $repo "bench\quickstart_config.py") weights-state --mode $Mode 2>$null
if ($LASTEXITCODE -ne 0) { Fail "weights-state failed" "python exited $LASTEXITCODE" "see output above" }
$need = @((($wsJson -join "`n") | ConvertFrom-Json))
if (-not $need -or -not $need[0].rel) { Fail "weights-state parse failed" "could not parse quickstart_config.py output" "run: python -I bench\quickstart_config.py weights-state --mode $Mode" }
foreach ($w in $need) {
    $dest = Join-Path $repo (Join-Path "weights\comfyui-split" $w.rel)
    if ($w.state -eq "absent" -and $SkipSetup) {
        Fail "-SkipSetup but weights missing" "$($w.rel) is absent" "rerun without -SkipSetup to download (resumable)"
    }
    if ($w.state -ne "present") {
        Write-Host "[download] $($w.rel) ($([math]::Round($w.expected_bytes/1GB,2)) GB) - resumable, safe to Ctrl+C and rerun"
        New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
        & $py -I (Join-Path $repo "tools\download_parallel.py") "$hfBase/resolve/$($w.revision)/$($w.rel)" $dest 16
        if ($LASTEXITCODE -ne 0) { Fail "download failed" "tools/download_parallel.py exited $LASTEXITCODE for $($w.rel)" "rerun the same command - chunks resume byte-exact" }
    }
    # digest verification runs for EVERY file on EVERY invocation (review
    # P0-4); the stamp cache makes repeat checks fast but is keyed on
    # size+mtime, so any change re-hashes
    $vJson = & $py -I (Join-Path $repo "bench\quickstart_config.py") verify-weight --rel $w.rel 2>$null
    if ($LASTEXITCODE -ne 0) { Fail "digest check crashed" "verify-weight exited $LASTEXITCODE for $($w.rel)" "see output above" }
    $v = ($vJson -join "`n") | ConvertFrom-Json
    if (-not $v.ok) {
        if ($w.state -eq "present") {
            Fail "weight integrity FAILED (pinned digest mismatch)" "$($w.rel): local sha256 does not match the pinned digest (same-size corruption or wrong file)" "delete the file and rerun to re-download, or restore from a trusted copy"
        }
        # fresh download failed digest: one re-download attempt, then fail
        & $py -I (Join-Path $repo "tools\download_parallel.py") "$hfBase/resolve/$($w.revision)/$($w.rel)" $dest 16
        $vJson = & $py -I (Join-Path $repo "bench\quickstart_config.py") verify-weight --rel $w.rel 2>$null
        $v = ($vJson -join "`n") | ConvertFrom-Json
        if (-not $v.ok) { Fail "weight integrity FAILED after re-download" "$($w.rel): sha256 still does not match the pinned digest" "report the mirror; source pinned digests live in bench/quickstart_config.py" }
    }
    Write-Host "[ok] $($w.rel) sha256 verified (pinned revision $($w.revision.Substring(0,8)))"
}

# --- 9. start server (port-safe: NEVER touch an existing listener) -----------
$Port = Select-ServerPort $Port
if ($Port -lt 0) { Fail "no free port" "ports exhausted the search window" "free a port or pass -Port <n>" }
Write-Host "[5/6] starting ComfyUI (sdp=$($cfg.sdp_mode) flags=$($cfg.server_flags -join ' ')) on port $Port..."
$tServerStart = Get-Date
$resultsDir = Join-Path $repo (Join-Path "bench\results\quickstart" ("$Mode-" + (Get-Date -Format 'yyyyMMdd-HHmmss')))
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null   # must exist before Start-Process redirects logs into it
$launch = Join-Path $repo "phase2-comfyui\launch_comfyui.ps1"
$flagStr = $cfg.server_flags -join " "
$argStr = "-NoProfile -ExecutionPolicy Bypass -File `"$launch`" -Port $Port -SdpMode $($cfg.sdp_mode)"
if ($flagStr) { $argStr += " -ComfyArgs `"$flagStr`"" }
$server = Start-Process -FilePath "powershell" -ArgumentList $argStr -PassThru `
    -RedirectStandardOutput (Join-Path $resultsDir "server.log") -RedirectStandardError (Join-Path $resultsDir "server.err.log") `
    -WindowStyle Hidden
$script:ServerProc = $server
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
# remember OUR exact process tree while the root is alive (PID ownership,
# never name matching)
$script:OwnPids = Get-DescendantPids $server.Id
Write-Host "[ok] server healthy in ${bootS}s - GPU: $($dev.name) (VRAM $([math]::Round($dev.vram_total/1GB,1)) GB); own tree PIDs: $($server.Id)$(if ($script:OwnPids) { ', ' + ($script:OwnPids -join ', ') })"

# --- 10. smoke generation through the benchmark driver ------------------------
Write-Host "[6/6] generating (cold + warm) via the benchmark driver..."
$runTag = Split-Path -Leaf $resultsDir
$driverArgs = @("run", "--python", "3.12", "--with", "requests", "--with", "websocket-client", "--with", "jsonschema",
    "python", "-I", (Join-Path $repo "bench\run_comfyui.py"),
    "--date", "quickstart/$runTag",
    "--experiment", $manifestName,
    "--base-url", "http://127.0.0.1:$Port",
    "--only-prompt", $Prompt, "--measured", "2", "--session", "quickstart")
if ($Resolution -ne $cfg.resolution) { $driverArgs += @("--resolution", "$Resolution") }
& $uv @driverArgs
$driverCode = $LASTEXITCODE
if ($driverCode -ne 0) {
    Fail "generation failed" "bench/run_comfyui.py exited $driverCode" "see driver output above; check server logs in $resultsDir"
}

# --- 11. report (unified cold-start vocabulary, review P0-6) ------------------
$records = Get-ChildItem $resultsDir -Filter *.json | Where-Object { $_.Name -ne "provisioning.json" } |
    ForEach-Object { Get-Content $_.FullName -Raw | ConvertFrom-Json }
$cold = $records | Where-Object { $_.run_kind -eq "cold" } | Select-Object -First 1
$measures = @($records | Where-Object { $_.run_kind -eq "measure" })
$warmVals = @($measures | ForEach-Object { [double]$_.runs[0].total_s } | Sort-Object)
$warmMean = if ($warmVals) { [math]::Round(($warmVals | Measure-Object -Average).Average, 2) } else { 0 }
$warmMedian = if ($warmVals) { [math]::Round($warmVals[[int](($warmVals.Count - 1) / 2)], 2) } else { 0 }
$tDone = Get-Date
$fullColdS = if ($cold) { [math]::Round($bootS + [double]$cold.runs[0].total_s, 1) } else { 0 }
$imgs = Get-ChildItem (Join-Path $repo (Join-Path "results\raw\quickstart" $runTag)) -Filter *.png -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "==================== quickstart done ====================" -ForegroundColor Green
Write-Host ("mode={0}  resolution={1}  steps={2}  prompt={3}   stack_verified={4}" -f $Mode, $Resolution, $cfg.steps, $Prompt, $StackVerified)
Write-Host ("GPU: {0}   torch: {1}   ComfyUI: {2}" -f $dev.name, $TorchPin, $headCommit)
Write-Host ("Server boot               (launch -> healthy):        {0} s" -f $bootS)
if ($cold) { Write-Host ("Ready-to-first-image      (healthy -> 1st PNG incl. load): {0} s  [TE {1} s, denoise+load {2} s, VAE {3} s]" -f [math]::Round($cold.runs[0].total_s,1), [math]::Round($cold.runs[0].text_encode_s,2), [math]::Round($cold.runs[0].denoise_s,2), [math]::Round($cold.runs[0].vae_decode_s,2)) }
Write-Host ("Full cold start           (launch -> 1st PNG):         {0} s" -f $fullColdS)
Write-Host ("Warm (same prompt, TE cached): mean {0} s / median {1} s  (n={2})" -f $warmMean, $warmMedian, $measures.Count)
Write-Host ("total wall clock this run:  {0} s" -f [math]::Round(($tDone - $tServerStart).TotalSeconds, 1))
if ($imgs) {
    Write-Host "images:" -ForegroundColor Green
    $imgs | ForEach-Object { Write-Host "  $($_.FullName)" }
}
Write-Host ("records: {0}" -f $resultsDir)
Write-Host "note: fresh-prompt cost = warm + a real text-encode (~1.2 s int8 / 3-7 s bf16);"
Write-Host "      first-ever run adds a one-time weight download (~18 GB Fast / ~32 GB Quality)."
Write-Host "=========================================================" -ForegroundColor Green

# provenance record (review P0-5): what ran, on which stack, verified or not
@{
    mode = $Mode; resolution = $Resolution; prompt = $Prompt; port = $Port
    comfy_commit = "$headCommit"; comfy_commit_pinned = $ComfyCommit
    torch = $TorchPin; stack_verified = $StackVerified
    server_root_pid = $server.Id; own_pids = $script:OwnPids
    server_boot_s = $bootS
    ready_to_first_image_s = if ($cold) { [math]::Round($cold.runs[0].total_s, 2) } else { $null }
    full_cold_start_s = $fullColdS
    warm_mean_s = $warmMean; warm_median_s = $warmMedian; warm_n = $measures.Count
    finished_at = (Get-Date -Format s)
} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $resultsDir "provisioning.json")

# --- 12. teardown (own process tree ONLY; -KeepServer honored) ----------------
if ($KeepServer) {
    Write-Host "server left running: http://127.0.0.1:$Port (root PID $($server.Id)$(if ($script:OwnPids) { ", children " + ($script:OwnPids -join ',') }))" -ForegroundColor Yellow
    Write-Host "stop it with:  taskkill /PID $($server.Id) /T /F"
} else {
    Stop-OwnTree $server.Id $script:OwnPids $Port
    Write-Host "server stopped (own tree only)"
}
exit 0

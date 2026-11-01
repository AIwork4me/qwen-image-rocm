# Phase 3 variant runner: full ComfyUI server lifecycle per experiment variant.
#
#   start server (manifest flags) -> 7900 health gate -> run driver ->
#   POST /free -> attention-log evidence -> kill process tree -> port check
#
# Every variant (incl. bf16 controls) runs on a freshly started server so
# restart regime is identical across comparisons; probes that OOM leave no
# wedged state behind.
#
# Usage:
#   powershell -File bench\run_variant.ps1 -Experiment p3-turbo-8step-1024x1024 -Date 2026-11-01-e1
#   (-Resolution 2048 for probes; -Session/-RestartIdx recorded into records)
param(
    [Parameter(Mandatory = $true)][string]$Experiment,
    [Parameter(Mandatory = $true)][string]$Date,
    [int]$Port = 8188,
    [int]$Resolution = 0,
    [string]$Session = "",
    [int]$RestartIdx = 0,
    [int]$HealthTimeoutS = 600,
    [string]$OnlyPrompt = "",
    [int]$Measured = 0
)

$ErrorActionPreference = "Continue"  # Phase-1 lesson: native stderr must not kill PS5.1
$repo = Split-Path -Parent $PSScriptRoot
$launch = Join-Path $repo "phase2-comfyui\launch_comfyui.ps1"
$uvCandidates = @(
    "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe",
    (Get-Command uv -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
)
$uv = $uvCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $uv) { Write-Error "uv.exe not found"; exit 2 }

$manifestPath = Join-Path $repo "bench\experiments\$Experiment.json"
if (-not (Test-Path $manifestPath)) { Write-Error "no manifest: $manifestPath"; exit 2 }
$m = Get-Content $manifestPath -Raw | ConvertFrom-Json
$resultsDir = Join-Path $repo "bench\results\$Date"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$serverOut = Join-Path $resultsDir "server.log"
$serverErr = Join-Path $resultsDir "server.err.log"

function Test-PortBusy([int]$p) {
    [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}

# Kill ONLY processes this repo spawned. A leftover server from a previous
# (crashed) run references phase2-comfyui in its command line; an unrelated
# listener (user's own ComfyUI, any other service) does not and is NEVER
# touched — the caller picks a spare port instead.
function Kill-OwnOrphans([int]$p) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -le 0) { continue }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)" -ErrorAction SilentlyContinue
        $cmd = if ($proc) { "$($proc.CommandLine)" } else { "" }
        if ($cmd -match "phase2-comfyui") {
            Write-Host "killing orphaned server PID $($c.OwningProcess) on port $p (command line references this repo)"
            taskkill /PID $c.OwningProcess /T /F 2>$null | Out-Null
        } else {
            $pname = if ($proc) { $proc.Name } else { "unknown" }
            Write-Warning "port $p is owned by unrelated process PID $($c.OwningProcess) ($pname); NOT killing it"
        }
    }
    Start-Sleep 2
}

# --- 1. clean slate (port-safe: never kill a process we did not start) ------
Kill-OwnOrphans $Port
$originalPort = $Port
while (Test-PortBusy $Port) {
    Write-Warning "port $Port still in use; trying next port"
    $Port++
    if ($Port -gt ($originalPort + 20)) {
        Write-Error "no free port in $originalPort..$($originalPort + 20); aborting without killing anything"
        exit 5
    }
}
if ($Port -ne $originalPort) { Write-Host "using spare port $Port (requested $originalPort was busy)" }

# --- 2. start server with the variant's flags -------------------------------
# manifest optional fields are also baked into the JSON; defaults here are
# belt-and-braces so a hand-edited manifest cannot null-bind Start-Process
$sdp = "$($m.sdp_mode)"; if (-not $sdp) { $sdp = "math" }
$flags = @()
if ($m.server_flags) { $flags = @($m.server_flags) }
if ($m.env_vars) {
    foreach ($prop in $m.env_vars.PSObject.Properties) {
        Set-Item -Path ("Env:" + $prop.Name) -Value "$($prop.Value)"
        Write-Host "env: $($prop.Name)=$($prop.Value)"
    }
}
$flagStr = ($flags -join " ")
$argStr = "-NoProfile -ExecutionPolicy Bypass -File `"$launch`" -Port $Port -SdpMode $sdp"
if ($flagStr) { $argStr += " -ComfyArgs `"$flagStr`"" }
$server = Start-Process -FilePath "powershell" -ArgumentList $argStr -PassThru `
    -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr `
    -WindowStyle Hidden
if (-not $server -or $server.Id -le 0) {
    Write-Error "failed to start server process"
    exit 4
}
Write-Host "server PID $($server.Id) starting (sdp=$sdp flags=$flagStr)"

# --- 3. health gate: /system_stats must report the 7900 ----------------------
$deadline = (Get-Date).AddSeconds($HealthTimeoutS)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep 3
    if ($server.HasExited) { break }
    try {
        $stats = Invoke-RestMethod "http://127.0.0.1:$Port/system_stats" -TimeoutSec 5
        $gpu = $stats.devices | Where-Object { $_.name -match "7900" }
        if ($gpu) { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) {
    Write-Error "server failed health gate in ${HealthTimeoutS}s; log tail:"
    if (Test-Path $serverOut) { Get-Content $serverOut -Tail 30 }
    if (Test-Path $serverErr) { Get-Content $serverErr -Tail 30 }
    if (-not $server.HasExited) { taskkill /PID $server.Id /T /F 2>$null | Out-Null }
    exit 3
}
Write-Host "server healthy on port $Port"

# --- 4. run the driver -------------------------------------------------------
$driverArgs = @("run", "--python", "3.12",
    "--with", "requests", "--with", "websocket-client", "--with", "jsonschema",
    "python", "-I", (Join-Path $repo "bench\run_comfyui.py"),
    "--date", $Date, "--experiment", $Experiment,
    "--base-url", "http://127.0.0.1:$Port",
    "--restart-idx", "$RestartIdx")
if ($Session) { $driverArgs += @("--session", $Session) }
if ($Resolution -gt 0) { $driverArgs += @("--resolution", "$Resolution") }
if ($OnlyPrompt) { $driverArgs += @("--only-prompt", $OnlyPrompt) }  # smoke only
if ($Measured -gt 0) { $driverArgs += @("--measured", "$Measured") } # smoke only
Write-Host "uv $($driverArgs -join ' ')"
& $uv @driverArgs
$driverCode = $LASTEXITCODE

# --- 5. free models/memory (best effort) -------------------------------------
try {
    Invoke-RestMethod -Method Post "http://127.0.0.1:$Port/free" `
        -ContentType "application/json" -TimeoutSec 30 `
        -Body '{"unload_models": true, "free_memory": true}' | Out-Null
    Write-Host "POST /free ok"
} catch { Write-Host "POST /free skipped: $_" }

# --- 6. attention evidence from the SERVER LOG -------------------------------
$evidence = Join-Path $resultsDir "attention_evidence.txt"
$lines = @()
foreach ($f in @($serverOut, $serverErr)) {
    if (Test-Path $f) {
        $lines += Select-String -Path $f -Pattern "attention|quadratic|disabling|Native ops|emulated" -ErrorAction SilentlyContinue |
            ForEach-Object { "$(Split-Path -Leaf $f):$($_.LineNumber): $($_.Line)" }
    }
}
if ($lines) { $lines | Set-Content -Encoding UTF8 $evidence; Write-Host "attention evidence -> $evidence" }
else { Write-Warning "no attention/native-ops lines found in server log" }

# --- 7. teardown + verify (own process tree only) -----------------------------
if (-not $server.HasExited) { taskkill /PID $server.Id /T /F 2>$null | Out-Null }
Start-Sleep 2
Kill-OwnOrphans $Port   # orphaned child of ours only; never an unrelated listener
$portFree = -not (Test-PortBusy $Port)
if (-not $portFree) {
    Write-Warning "port $Port still busy after teardown; owner is not ours, leaving it alone"
}
Write-Host "teardown done; port free: $portFree; driver exit: $driverCode"
exit $driverCode

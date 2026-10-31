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
    [int]$HealthTimeoutS = 600
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

function Kill-Port([int]$p) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -gt 0) {
            Write-Host "killing PID $($c.OwningProcess) on port $p"
            taskkill /PID $c.OwningProcess /T /F 2>$null | Out-Null
        }
    }
    Start-Sleep 2
}

# --- 1. clean slate ---------------------------------------------------------
Kill-Port $Port

# --- 2. start server with the variant's flags -------------------------------
foreach ($prop in $m.env_vars.PSObject.Properties) {
    Set-Item -Path "Env:$($prop.Name)" -Value $prop.Value
    Write-Host "env: $($prop.Name)=$($prop.Value)"
}
$launchArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $launch,
    "-Port", "$Port", "-SdpMode", "$($m.sdp_mode)")
if ($m.server_flags) {
    $launchArgs += @("-ComfyArgs", ($m.server_flags -join " "))
}
$server = Start-Process powershell -ArgumentList $launchArgs -PassThru `
    -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr `
    -WindowStyle Hidden
Write-Host "server PID $($server.Id) starting (sdp=$($m.sdp_mode) flags=$($m.server_flags -join ' '))"

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
    Kill-Port $Port
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

# --- 7. teardown + verify -----------------------------------------------------
if (-not $server.HasExited) { taskkill /PID $server.Id /T /F 2>$null | Out-Null }
Kill-Port $Port
$portFree = -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
Write-Host "teardown done; port free: $portFree; driver exit: $driverCode"
exit $driverCode

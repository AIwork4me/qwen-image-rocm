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
    [int]$Measured = 0,
    [switch]$OverwriteResults
)

$ErrorActionPreference = "Continue"  # Phase-1 lesson: native stderr must not kill PS5.1
$repo = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "portops.ps1")
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
# overwrite guard (review P1-10): an existing run's records are evidence;
# refuse to clobber them unless explicitly told to
if (Test-Path $resultsDir) {
    $existing = @(Get-ChildItem $resultsDir -Filter *.json -ErrorAction SilentlyContinue)
    if ($existing.Count -gt 0 -and -not $OverwriteResults) {
        Write-Error "results dir already contains $($existing.Count) record(s): $resultsDir - use a new -Date or pass -OverwriteResults to clobber deliberately"
        exit 6
    }
}
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$serverOut = Join-Path $resultsDir "server.log"
$serverErr = Join-Path $resultsDir "server.err.log"

# --- 1. clean slate (port-safe: NEVER touch an existing listener; review P0-3)
# Ownership = PIDs of the tree WE start in this invocation (portops.ps1).
# Anything already listening - even a leftover server from a previous run of
# THIS repo - is left alone; we simply take the next free port.
$Port = Select-ServerPort $Port
if ($Port -lt 0) { Write-Error "no free port in the search window"; exit 5 }

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
    Stop-OwnTree $server.Id @() $Port   # our own tree only; strangers untouched
    exit 3
}
$ownPids = Get-DescendantPids $server.Id   # remember OUR tree while root is alive
Write-Host "server healthy on port $Port (root PID $($server.Id)$(if ($ownPids) { ', children ' + ($ownPids -join ',') }))"

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

# --- 7. teardown (own process tree ONLY, by PID; review P0-3) -----------------
Stop-OwnTree $server.Id $ownPids $Port
$portFree = -not (Test-PortBusy $Port)
Write-Host "teardown done; port free: $portFree; driver exit: $driverCode"
exit $driverCode

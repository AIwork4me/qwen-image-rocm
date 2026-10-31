# Download Comfy-Org split weights via hf-mirror with a stall watchdog.
# Procedure from docs/weights.md (Phase 2, mainland-network measured):
#   - HF_ENDPOINT=https://hf-mirror.com (direct HF unreachable)
#   - HF_HUB_DISABLE_XET=1 (xet CAS endpoints not proxied by the mirror)
#   - the mirror dies mid-transfer every few GB without exiting -> watchdog
#     kills hf after $StallSeconds without progress; hf resumes .incomplete
#     files on restart, so restarts are cheap.
#
# Usage:
#   powershell -File tools\download_weights.ps1 -Include diffusion_models/x.safetensors,text_encoders/y.safetensors
#   (comma-separated list, or pass -Include twice)
param(
    [string[]]$Include,
    [string]$Repo = "Comfy-Org/Qwen-Image-2.1",
    [string]$LocalDir = "weights/comfyui-split",
    [int]$StallSeconds = 300,
    [int]$MaxRestarts = 40,
    [int]$PollSeconds = 15
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$hf = Join-Path $repoRoot "phase2-comfyui\.venv\Scripts\hf.exe"
if (-not (Test-Path $hf)) { Write-Error "hf.exe not found: $hf"; exit 2 }

$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DISABLE_XET = "1"

# comma-separated convenience: -Include "a,b" -> ["a","b"]
$patterns = @()
foreach ($item in $Include) { $patterns += ($item -split ",") | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
if (-not $patterns) { Write-Error "no --include patterns"; exit 2 }

$args = @("download", $Repo)
foreach ($p in $patterns) { $args += @("--include", $p) }
$args += @("--local-dir", (Join-Path $repoRoot $LocalDir))
Write-Host "hf $($args -join ' ')"

function Get-IncompleteBytes {
    (Get-ChildItem -Recurse -Filter *.incomplete -Path (Join-Path $repoRoot $LocalDir) -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
}

for ($i = 0; $i -le $MaxRestarts; $i++) {
    $p = Start-Process -FilePath $hf -ArgumentList $args -PassThru -NoNewWindow
    $lastSize = -1L
    $lastChange = Get-Date
    while (-not $p.HasExited) {
        Start-Sleep -Seconds $PollSeconds
        if ($p.HasExited) { break }
        $size = Get-IncompleteBytes
        if ($null -eq $size) { $size = 0L }
        if ($size -ne $lastSize) {
            $lastSize = $size
            $lastChange = Get-Date
            Write-Host ("[{0}] downloading... {1:N0} MB in .incomplete" -f (Get-Date -Format HH:mm:ss), ($size / 1MB))
        } elseif (((Get-Date) - $lastChange).TotalSeconds -gt $StallSeconds) {
            Write-Host "stall > ${StallSeconds}s -- killing hf for resume (attempt $($i+1))"
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            break
        }
    }
    try { $p.WaitForExit() } catch {}
    if ($p.ExitCode -eq 0) {
        Write-Host "download complete."
        Get-ChildItem -Recurse -File (Join-Path $repoRoot $LocalDir) |
            Where-Object { $_.Name -match 'turbo|int8|w4a8' } |
            ForEach-Object { Write-Host ("  {0}  {1:N0} MB" -f $_.FullName.Replace($repoRoot, ""), ($_.Length / 1MB)) }
        exit 0
    }
    Write-Host "hf exited $($p.ExitCode); restarting ($($i+1)/$MaxRestarts)"
}
Write-Error "download did not finish after $MaxRestarts restarts"
exit 1

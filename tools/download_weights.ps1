# Download Comfy-Org split weights via hf-mirror with byte-exact resume.
#
# REWRITE 2026-10-31: the previous hf-CLI watchdog approach wasted massive
# bandwidth — hf's parallel-chunk .incomplete part-files do NOT resume after
# a forceful kill; every watchdog restart opened a fresh set (measured: ~38GB
# of partials for ~8GB of real progress). curl -C - resumes byte-exact on a
# single .part file, and --speed-limit aborts stalls so the retry loop can
# restart quickly. Direct HF unreachable -> hf-mirror per docs/weights.md.
#
# Usage:
#   powershell -File tools\download_weights.ps1 -Include diffusion_models/x.safetensors,text_encoders/y.safetensors
param(
    [string[]]$Include,
    [string]$Repo = "Comfy-Org/Qwen-Image-2.1",
    [string]$LocalDir = "weights/comfyui-split",
    [int]$MaxRetries = 100
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$base = "https://hf-mirror.com/$Repo/resolve/main"

$patterns = @()
foreach ($item in $Include) { $patterns += ($item -split ",") | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
if (-not $patterns) { Write-Error "no -Include patterns"; exit 2 }

foreach ($rel in $patterns) {
    $out = Join-Path (Join-Path $repoRoot $LocalDir) ($rel -replace "/", "\")
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null
    $part = "$out.part"
    $done = $false
    for ($i = 1; $i -le $MaxRetries; $i++) {
        # --speed-limit/--speed-time: abort if <20 KB/s for 120 s (stall watchdog
        # INSIDE curl); -C - resumes the same .part file byte-exact.
        & curl.exe -L -C - --fail --retry 3 --speed-limit 20480 --speed-time 120 -o $part "$base/$rel"
        if ($LASTEXITCODE -eq 0) {
            Move-Item -Force $part $out
            $mb = [math]::Round((Get-Item $out).Length / 1MB)
            Write-Host "DONE $rel ($mb MB)"
            $done = $true
            break
        }
        $sz = 0; if (Test-Path $part) { $sz = [math]::Round((Get-Item $part).Length / 1MB) }
        Write-Host "retry $i/$MaxRetries for $rel (have $sz MB, curl exit $LASTEXITCODE)"
        Start-Sleep -Seconds 3
    }
    if (-not $done) { Write-Error "FAILED: $rel did not finish after $MaxRetries retries"; exit 1 }
}
Write-Host "all downloads complete"
exit 0

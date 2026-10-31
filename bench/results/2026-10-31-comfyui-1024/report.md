# Phase 1 diffusers baseline report

- Protocol: `v1`
- Runs per config: median of 3
- Environment: `snapshot-20261030-212234.json`

| Config | Prompt | median total (s) | min–max (s) | s/step | VRAM (MB) | n |
|---|---|---|---|---|---|---|
| p2-comfyui-1024x1024 | p1-zh-scene | 50.5 | 48.3–51.4 | n/a | 16561 | 3 |
| p2-comfyui-1024x1024 | p2-en-scene | 51.4 | 51.4–51.5 | n/a | 16561 | 3 |
| p2-comfyui-1024x1024 | p3-poster-text | 45.4 | 45.4–45.6 | n/a | 16561 | 3 |

Cold run (first load, p2-comfyui-1024x1024, p1-zh-scene): 680.289s total, denoise 363.209s.

## Limitations

- Single machine, single GPU (AMD Radeon RX 7900 XTX, Windows-native ROCm);
  numbers are not comparable across machines or driver versions.
- `step_times_s[0]` includes text-encode and cpu-offload weight restore
  besides step 1's compute; the s/step column is the median of steps 2..N
  (steady state). `denoise_s` sums ALL steps and carries the same step-1
  tax — do not divide it by `steps` to get a per-step rate.
- Protocol v1.1 (2026-10-31): s/step semantics corrected from
  `denoise_s/steps` to the steady-state median; v1.0 reports overstated
  it (e.g. math backend at 1024²: ~5.9 reported vs ~3.7 true).
- Median of 3 measured runs per config; variance between runs is reported
  as min–max, not confidence intervals.
- No cross-framework claim: diffusers-only in this report.

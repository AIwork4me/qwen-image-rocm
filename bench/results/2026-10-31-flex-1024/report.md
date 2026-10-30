# Phase 1 diffusers baseline report

- Protocol: `v1`
- Runs per config: median of 3
- Environment: `snapshot-20261030-212234.json`

| Config | Prompt | median total (s) | min–max (s) | s/step | VRAM (MB) | n |
|---|---|---|---|---|---|---|
| p1-bf16-1024x1024 | p1-zh-scene | 875.1 | 863.9–886.6 | 18.94 | 20908 | 3 |
| p1-bf16-1024x1024 | p2-en-scene | 755.8 | 746.3–780.1 | 16.12 | 20778 | 3 |
| p1-bf16-1024x1024 | p3-poster-text | 853.2 | 841.8–857.4 | 18.88 | 20819 | 3 |

Cold run (first load, p1-bf16-1024x1024, p1-zh-scene): 1031.515s total, denoise 1004.604s.

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

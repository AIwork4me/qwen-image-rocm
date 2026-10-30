# Phase 1 diffusers baseline report

- Protocol: `v1`
- Runs per config: median of 3
- Environment: `snapshot-20261030-212234.json`

| Config | Prompt | median total (s) | min–max (s) | s/step | VRAM (MB) | n |
|---|---|---|---|---|---|---|
| p1-bf16-1024x1024 | p1-zh-scene | 250.5 | 247.5–261.2 | 5.88 | 18832 | 3 |
| p1-bf16-1024x1024 | p2-en-scene | 254.0 | 243.6–260.7 | 5.94 | 18806 | 3 |
| p1-bf16-1024x1024 | p3-poster-text | 239.0 | 218.0–242.6 | 5.72 | 18856 | 3 |

Cold run (first load, p1-bf16-1024x1024, p1-zh-scene): 188.706s total, denoise 164.441s.

## Limitations

- Single machine, single GPU (AMD Radeon RX 7900 XTX, Windows-native ROCm);
  numbers are not comparable across machines or driver versions.
- Text-encode and VAE-decode stages are not separately timed in this phase;
  `denoise_s` covers the denoising loop only (see run_bench.py header).
- Median of 3 measured runs per config; variance between runs is reported
  as min–max, not confidence intervals.
- No cross-framework claim: diffusers-only in this report.

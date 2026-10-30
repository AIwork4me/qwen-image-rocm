# Phase 1 diffusers baseline report

- Protocol: `v1`
- Runs per config: median of 3
- Environment: `snapshot-20261030-212234.json`

| Config | Prompt | median total (s) | min–max (s) | s/step | VRAM (MB) | n |
|---|---|---|---|---|---|---|
| p1-bf16-1024x1024 | p1-zh-scene | 875.1 | 863.9–886.6 | 21.59 | 20908 | 3 |
| p1-bf16-1024x1024 | p2-en-scene | 755.8 | 746.3–780.1 | 18.55 | 20778 | 3 |
| p1-bf16-1024x1024 | p3-poster-text | 853.2 | 841.8–857.4 | 21.17 | 20819 | 3 |

Cold run (first load, p1-bf16-1024x1024, p1-zh-scene): 1031.515s total, denoise 1004.604s.

## Limitations

- Single machine, single GPU (AMD Radeon RX 7900 XTX, Windows-native ROCm);
  numbers are not comparable across machines or driver versions.
- Text-encode and VAE-decode stages are not separately timed in this phase;
  `denoise_s` covers the denoising loop only (see run_bench.py header).
- Median of 3 measured runs per config; variance between runs is reported
  as min–max, not confidence intervals.
- No cross-framework claim: diffusers-only in this report.

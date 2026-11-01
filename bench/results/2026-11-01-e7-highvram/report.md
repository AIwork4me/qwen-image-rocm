# Phase 1 diffusers baseline report

- Protocol: `v1.3`
- Runs per config: median of 5
- Environment: `snapshot-20261030-212234.json`

| Config | Prompt | median total (s) | min–max (s) | s/step | VRAM (MB) | n |
|---|---|---|---|---|---|---|
| p3-vram-highvram-1024x1024 | p1-zh-scene | 43.4 | 43.3–43.5 | 1.06 | 15289 | 5 |
| p3-vram-highvram-1024x1024 | p2-en-scene | 45.4 | 45.3–45.5 | 1.10 | 15117 | 5 |
| p3-vram-highvram-1024x1024 | p3-poster-text | 163.0 | 160.5–173.2 | 0.99 | 24395 | 5 |

Cold run (first load, p3-vram-highvram-1024x1024, p1-zh-scene): 107.25s total, denoise 106.309s.

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


- Protocol v1.2 (2026-10-31): cold/warmup seeds are seeds[0]+1e6
  so ComfyUI's execution cache can never serve a cached result to a
  measured run (v1.0/v1.1 warmups shared the measured seed).
- Protocol v1.3 (Phase 3, 2026-10-31): warmup seed is now seeds[0]+2e6
  (v1.2 warmups were input-identical to the cold run — graph-cache
  no-ops instead of executing warmups); ComfyUI records carry /ws
  node/step timing (text_encode_s, vae_decode_s, ksampler_s,
  step_times_s) and a true VRAM peak (0.5 s /system_stats sampling;
  vram_residency_mb keeps the old post-run metric).
- ComfyUI TE-cache caveat (corrected 2026-10-31): measured runs change
  only the seed, so CLIPTextEncode is a node-cache hit — text encode
  is NOT inside measured denoise_s/total_s. Real TE cost: cold runs,
  fresh_prompt runs (prompt+' .' busts the cache), or text_encode_s.

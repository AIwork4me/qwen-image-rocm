# Quality gate — p3-w4a8-te-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e2-w4a8-te`
- LPIPS semantics: FIDELITY — same model, same seed, only the numerics path changed (quantization / attention backend). Lower = closer to the bf16 reference; compare against the noise floor before reading anything into small values.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.1888 | 0.4127 | 3 |
| p2-en-scene | 0.0872 | 0.1434 | 3 |
| p3-poster-text | 0.0426 | 0.0661 | 3 |

## Verdict (user final — 三档终审)

- [ ] 无感 (imperceptible)
- [x] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: user 2026-11-01: A5 略降 → w4a8 拒绝，int8 TE 为替代

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

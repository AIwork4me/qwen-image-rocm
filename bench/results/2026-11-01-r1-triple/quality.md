# Quality gate — p3-turbo-int8-ck-te-nosmart-1024x1024

- Baseline: `results/raw/2026-11-01-e8-turbo-int8-ck` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-r1-triple`
- LPIPS semantics: FIDELITY — same model, same seed, only the numerics path changed (quantization / attention backend). Lower = closer to the bf16 reference; compare against the noise floor before reading anything into small values.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.0583 | 0.0748 | 3 |
| p2-en-scene | 0.0115 | 0.0150 | 3 |
| p3-poster-text | 0.0137 | 0.0154 | 3 |

## Verdict (user final — 三档终审)

- [ ] 无感 (imperceptible)
- [ ] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: 

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

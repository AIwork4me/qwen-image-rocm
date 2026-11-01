# Quality gate — p3-turbo-int8-ck-te-nosmart-1024x1024

- Baseline: `results/raw/2026-11-01-e8-turbo-int8-ck` (p3-turbo-int8-ck-1024x1024: int8-convrot, 8 steps, qwen_image_2.1_turbo_int8_convrot, TE bf16)
- Experiment: `results/raw/2026-11-01-r1-triple`
- LPIPS semantics: FIDELITY — same model, same seed, only the numerics path changed (quantization / attention backend). Lower LPIPS means closer perceptual similarity to the specified baseline image. LPIPS is not an absolute image-quality score; compare against the noise floor before reading anything into small values.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.0583 | 0.0748 | 3 |
| p2-en-scene | 0.0115 | 0.0150 | 3 |
| p3-poster-text | 0.0137 | 0.0154 | 3 |

## Verdict (user final — 三档终审)

OWNER VERDICT RECORDED 2026-11-01 ([#5 comment](https://github.com/AIwork4me/qwen-image-rocm/issues/5#issuecomment-6555955095) — verbatim):

- p1 Chinese scene: 略降
- p2 English scene: 无感
- p3 Typography poster: 不可接受

Outcome: **REJECTED as the Fast default** (any 不可接受 tier fails the
gate per the pre-published scale). Fast ships the E8 config (turbo int8
DiT + bf16 TE + ck) instead. Note: LPIPS fidelity (p3 median 0.0137) did
not predict the p3 verdict — the human gate is binding, exactly as
QUALITY_METHODOLOGY.md prescribes.

- [ ] 无感 (imperceptible) — p2
- [x] 略降 (slightly degraded) — p1
- [x] 不可接受 (unacceptable) — p3

Notes: overall gate FAILED (single 不可接受 tier rejects the config).

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

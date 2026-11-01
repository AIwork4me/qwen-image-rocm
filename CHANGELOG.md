# Changelog

## 2026-11-01 — Phase 3: optimization loop (protocol v1.3)

**1024-square: 5.2-5.5x faster (48s -> 9.1s)** via Turbo-8-step + native
int8 DiT + ck-attention (+ --disable-smart-memory). **2048-square unlocked**
(328s @40 steps; 42s with turbo-int8) — was impossible on bf16. Native int8
is near-lossless (LPIPS 0.004-0.031); w4a8 TE fails quality (0.41 max);
VAEDecodeTiled, --highvram, --fast fp16_accumulation all rejected with data.
torch.compile blocked: `TritonMissing` at inductor backend creation.
Measurement infra v1.3: websocket node/step timing, true VRAM peak,
manifest-driven variants, full server lifecycle per variant, quality gates
with determinism noise floor (0.0000). User verdicts RECORDED (turbo×3+ck 无感, w4a8 略降→rejected, 2048 praised);
AI second opinion (GLM-5.3-Flash) dual-confirmed: 5/5 match + 3 first
verdicts, 0 divergence >=1 grade (558ed07). Recommended configs final.


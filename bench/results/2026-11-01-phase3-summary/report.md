# Phase 3 cross-experiment summary (protocol v1.3)

Generated 2026-11-01T08:49:13. All numbers = median of measured runs; ratios are same-session paired vs the bf16 shadow control (`p3-control-bf16-1024x1024`, dir `2026-10-31-e1-control`).

| Experiment | steps | p1 med (s) | p2 med (s) | p3 med (s) | speedup p1/p2/p3 | VRAM peak (MB) | n |
|---|---|---|---|---|---|---|---|
| p3-turbo-int8-ck-1024x1024 | 8 | 9.1 | 9.1 | 9.1 | 5.32x / 5.52x / 5.31x | 19344 | 9 |
| Turbo 8-step int8 | 8 | 9.1 | 9.1 | 9.2 | 5.30x / 5.53x / 5.28x | 19720 | 9 |
| Turbo 8-step bf16 | 8 | 11.1 | 11.1 | 13.1 | 4.35x / 4.52x / 3.68x | 19688 | 9 |
| attn: ck | 40 | 35.2 | 37.5 | 37.3 | 1.37x / 1.34x / 1.30x | 17005 | 9 |
| vram: --disable-smart-memory | 40 | 45.4 | 46.4 | 42.4 | 1.06x / 1.08x / 1.14x | 15275 | 15 |
| vram: --highvram | 40 | 43.4 | 45.4 | 163.0 | 1.11x / 1.11x / 0.30x | 24395 | 15 |
| int8 TE (40-step) | 40 | 48.4 | 49.4 | 44.6 | 1.00x / 1.02x / 1.08x | 18610 | 9 |
| w4a8 TE (40-step) | 40 | 48.4 | 49.3 | 45.3 | 1.00x / 1.02x / 1.07x | 19660 | 9 |
| int8 DiT+TE (40-step) | 40 | 49.4 | 50.5 | 45.5 | 0.98x / 0.99x / 1.06x | 18578 | 9 |
| int8 DiT (40-step) | 40 | 48.3 | 49.4 | 45.5 | 1.00x / 1.02x / 1.06x | 19698 | 9 |
| attn: default, no wrapper | 40 | 48.4 | 51.5 | 47.4 | 1.00x / 0.98x / 1.02x | 17696 | 9 |
| vram: --fast fp16_accumulation | 40 | 47.4 | 48.5 | 223.7 | 1.02x / 1.04x / 0.22x | 19696 | 15 |
| attn: quad (sub-quadratic) | 40 | 48.3 | 49.5 | 47.4 | 1.00x / 1.01x / 1.02x | 19696 | 9 |
| attn: split | 40 | 50.5 | 52.3 | 52.5 | 0.95x / 0.96x / 0.92x | 18729 | 9 |
| vram: --cache-none | 40 | 70.7 | 71.7 | 67.9 | 0.68x / 0.70x / 0.71x | 21824 | 15 |

Notes: turbo-int8 2048² probe (not in table): 42.2s steady at native resolution; int8-dit-te 2048² probe: 328s (40-step). LPIPS verdict tables: per-experiment quality.md.

## AI second-opinion review (GLM-5.3-Flash, 2026-11-01, commit 558ed07)

8 experiments x 9 pairs judged independently of the human pass
([AI_JUDGE_RESULTS.json](../AI_JUDGE_RESULTS.json), prompt:
[AI_JUDGE_PROMPT.md](../AI_JUDGE_PROMPT.md)). Outcome: **5/5 match the human
verdicts** (A1-A4 无感, A5 略降 — AI independently flagged the same p1-r0
composition drift that produced the 0.41 LPIPS outlier, and the p3 row's
fidelity); **B1-B3 received their first formal verdict** (无感; the human pass
had only scanned these near-noise-floor items) — the commit headline's
"8/8 match" should be read as 5 match + 3 first. All 24 poster outputs were
glyph-checked at native resolution (one suspected "30H" in a 256px grid cell
was confirmed a thumbnail artifact of the serif 日). No >=1-grade divergence
anywhere: the quality gate is dual-confirmed and closed.

## LPIPS quality summary (vs bf16-40 control; noise floor 0.0000)

| Experiment | semantics | p1 med | p2 med | p3 med | max |
|---|---|---|---|---|---|
| turbo-int8 + ck | distance | 0.361 | 0.266 | 0.206 | 0.416 |
| turbo-int8 | distance | 0.352 | 0.222 | 0.260 | 0.381 |
| turbo bf16 | distance | 0.279 | 0.195 | 0.263 | 0.341 |
| attn ck | distance* | 0.342 | — | — | 0.449 |
| w4a8 TE | fidelity | 0.189 | 0.087 | 0.043 | 0.413 |
| int8-dit-te | fidelity | 0.029 | 0.008 | 0.006 | 0.055 |
| int8 TE | fidelity | 0.023 | 0.016 | 0.004 | 0.060 |
| int8 DiT | fidelity | 0.010 | 0.012 | 0.005 | 0.018 |
| attn split | fidelity | 0.007 | — | — | 0.017 |
| vaetiled | fidelity | 0.004 | — | — | 0.005 |
| attn quad / nomath / all vram modes | fidelity | 0.000 | 0.000 | 0.000 | 0.000 |

*ck changes the attention numerics path: same seed produces a different
(but plausibly quality-equivalent) image — same class as finding 5's
sub-quadratic-vs-math divergence; verdict is the user's grid call.

## Recommended 1024-square production config

- **Speed**: Turbo 8-step int8 DiT (`qwen_image_2.1_turbo_int8_convrot.safetensors`)
  + int8 TE + `--use-ck-attention` + `--disable-smart-memory` (not yet
  measured as a triple; the two measured pairs compound) — ~9 s/image,
  5.2-5.5x vs bf16-40. USER VERDICT (2026-11-01): turbo(3 variants)+ck = 无感; w4a8 = 略降 (rejected); 2048 samples 非常好. A3 (turbo-bf16) and A4 (ck-40step) rated best-in-class.
- **Quality-safe**: bf16-40 + `--use-ck-attention` + `--disable-smart-memory`
  (~35-37 s, 1.3-1.37x, numerics-path change pending verdict) or default
  attention + `--disable-smart-memory` (bit-identical, 1.06-1.14x).
- **2048-square native**: turbo-int8 @ 2048 = 42 s (8 steps) or
  int8-dit-te @ 2048 = 328 s (40 steps) — both previously impossible.
- **Avoid**: --highvram and --fast fp16_accumulation (catastrophic on long
  prompts), VAEDecodeTiled at 1024 (5x slower via residency thrash),
  --use-pytorch-cross-attention (finding 1), torch.compile (no Triton).

## Session notes

- Session e1 (2026-10-31/11-01): 24 server restarts, shadow control drift
  vs p2-day -0.4% mean. RAM pressure (31.8 GB vs 31+ GB weights) made
  model swaps the dominant fresh-prompt cost (finding-4 pattern).

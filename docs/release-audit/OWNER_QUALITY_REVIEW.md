# OWNER QUALITY REVIEW — production-triple grid (issue #5)

> **OUTCOME — VERDICT RECORDED 2026-11-01**
> ([#5 comment](https://github.com/AIwork4me/qwen-image-rocm/issues/5#issuecomment-6555955095),
> verbatim): p1 Chinese scene **略降** · p2 English scene **无感** · p3
> Typography poster **不可接受** → **the triple is REJECTED as the Fast
> default** per the pre-published scale. Consequence applied in the same
> revision: **Fast ships the E8 config** (turbo int8 DiT + bf16 TE + ck,
> judged 无感 A1), re-verified on GPU (warm mean 9.18 s / full cold
> 50.8 s). Notably LPIPS fidelity (p3 0.0137) did not predict the p3
> verdict — the human gate proved binding. The guide below is retained
> unchanged as the review record.

**This is the human-decision pack for the formal quality verdict. Nothing
here is a verdict yet.** The reviewer is the project owner; AI observations
(section K) are explicitly non-binding. Recording the verdict closes
[#5](https://github.com/AIwork4me/qwen-image-rocm/issues/5) and unblocks
the v0.1.0 stable tag.

## A. Configuration under review — "the full production triple"

| Field | Value |
|---|---|
| Experiment | `p3-turbo-int8-ck-te-nosmart-1024x1024` (records: `bench/results/2026-11-01-r1-triple/`) |
| DiT | `qwen_image_2.1_turbo_int8_convrot.safetensors` (native int8) |
| Text encoder | `qwen3vl_8b_int8_convrot.safetensors` (native int8) |
| VAE | `qwen_image_2.1_vae_bf16.safetensors` |
| Steps / sampler / cfg | 8 · euler/simple · 1.0 |
| Attention / memory | `--use-ck-attention` · `--disable-smart-memory` |
| Resolutions | 1024² (this grid) + 2048² (matrix, see H) |
| Stack | RX 7900 XTX · torch 2.12.0+rocm7.14.1 · ComfyUI `b5a43215` |

## B. Comparison baseline — E8 (already judged 无感, A1)

| Field | Value |
|---|---|
| Experiment | `p3-turbo-int8-ck-1024x1024` |
| DiT | turbo int8 (same as triple) |
| Text encoder | **bf16** (`qwen3vl_8b_bf16.safetensors`) ← the main delta |
| Steps / attention | 8 · ck (no `--disable-smart-memory`; that flag is bit-identical anyway) |
| Prior verdict | A1 无感 (user, 2026-11-01) + AI second opinion 无感 |

So this grid isolates: **what does switching the text encoder bf16 → int8
add on top of an already-accepted config?** (LPIPS fidelity vs E8.)

## C. Sample matrix (3 prompts × 3 seeds, 9 pairs)

`quality_grid.png` layout: **rows = prompts** (p1 zh scene / p2 en scene /
p3 zh typography poster), **columns = seeds** (r0 = seed 42, r1 = 1337,
r2 = 20261030), each cell **left = E8 baseline, right = production triple**,
labeled under each tile. All 18 source PNGs are the unedited measured
outputs (raw run records: `bench/results/2026-11-01-r1-triple/*.json`).

## D. LPIPS(alex) fidelity vs E8 — medians and maxima

| Prompt | median | max | n |
|---|---|---|---|
| p1-zh-scene | **0.0583** | **0.0748** | 3 |
| p2-en-scene | 0.0115 | 0.0150 | 3 |
| p3-poster-text | 0.0137 | 0.0154 | 3 |

Context bands (phase 3, same instrument, noise floor 0.0000): int8-TE
40-step fidelity 0.004–0.060; w4a8-TE (rejected) up to 0.413. Machine echo:
`quality.json` in the same directory (numbers pinned by
`tests/test_quality_gate_semantics.py` case 5).

## E. Direct review links (GitHub, this branch)

**Fastest path: the images are embedded directly in issue #5** (top
comment) — open the issue and they render inline. The links below are the
same evidence at full fidelity:

- **Paired grid (all 9 pairs, 1.7 MB, renders inline):**
  [bench/results/2026-11-01-r1-triple/quality_grid.png](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/bench/results/2026-11-01-r1-triple/quality_grid.png)
- **Per-prompt row strips (zoom-friendly views of the same grid):**
  [row1 p1](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/docs/release-audit/review-assets/r1-grid-row1-p1-zh-scene.png) ·
  [row2 p2](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/docs/release-audit/review-assets/r1-grid-row2-p2-en-scene.png) ·
  [row3 p3](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/docs/release-audit/review-assets/r1-grid-row3-p3-poster-text.png)
- **Native-resolution poster text crops (p3, the text-rendering case):**
  [bench/results/2026-11-01-r1-triple/quality_crops_poster.png](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/bench/results/2026-11-01-r1-triple/quality_crops_poster.png)
- **2048² typography sample** (5.3 MB — GitHub does not inline-render this
  size in issues; use the half-size preview
  [here](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/docs/release-audit/review-assets/p3-poster-2048-preview-half.jpg)
  or download the [original](https://github.com/AIwork4me/qwen-image-rocm/blob/release/trending-ready-v0.1.0/docs/gallery/fast-2048-p3-poster-seed42.png);
  no bf16 baseline exists at 2048 — eyeball only, supplementary)

Derived-view provenance:
[review-assets/PROVENANCE.md](review-assets/PROVENANCE.md).

Tip: download the grid locally and zoom — 256 px cells hide glyph-level
detail; use the poster crops for text.

## F. What to look at, per prompt

| Dimension | p1 zh scene | p2 en scene | p3 poster |
|---|---|---|---|
| Composition (layout/subject placement) | ● | ○ | ● |
| Detail & texture (water/brick/foliage vs rock/cloud gradients) | ● | ● | ○ |
| Lighting/color grade (golden-hour tone vs dawn light) | ● | ● | ○ |
| **Text accuracy — glyphs, strokes, spacing (native crops!)** | — | — | **●●** |
| Structural errors (extra/missing limbs, windows, boats) | ● | ● | ● |
| Visible artifacts (banding, ghosting, over-smoothing) | ● | ○ | ○ |

● = primary attention, ○ = secondary.

## G. What LPIPS can and cannot tell you here

LPIPS measures **perceptual similarity to the baseline image** — nothing
more. It cannot decide that the new image is *better* or *worse*, only that
it differs by some amount. A 0.058 median is "small but visible if you
look"; 0.011–0.014 is "nearly the same picture". The quality judgment is
yours, on the images.

## H. Where to look hardest — p1-zh-scene

p1 carries the largest divergence of the three (median 0.0583, max 0.0748 —
roughly 4–5× p2/p3). Mechanistically plausible cause: int8 text-encode
shifts conditioning, and p1's dense scene description (water reflections,
white walls, cooking smoke) amplifies small conditioning changes. Check p1
row first, especially r0/r1. Also note (context, not part of this gate):
the historical w4a8-TE failure mode was composition drift on p1-r0 — this
grid's p1 values sit far below that rejected band.

## I. Verdict scale (record in issue #5; also tick in quality.md)

| Tier | Definition |
|---|---|
| **无感** | Cannot reliably tell triple from E8 at normal viewing; would ship as default |
| **略降** | Noticeable on inspection but acceptable for the speed; may still ship as Fast default with a note |
| **不可接受** | Visible degradation in composition/text/artifacts; Fast stays on the e8-style config instead |

Record the verdict (per prompt or overall) as a comment on
[#5](https://github.com/AIwork4me/qwen-image-rocm/issues/5) — e.g.
"p1 略降, p2/p3 无感, overall 无感 → close". The checkbox block in
`bench/results/2026-11-01-r1-triple/quality.md` can be ticked in the same
change. Verdict recorded ⇒ #5 closes ⇒ stable-tag gate opens.

## J. What this verdict does NOT cover

- 2048² formal quality (no bf16 baseline can exist at 2048 on 24 GB —
  LPIPS N/A by construction; the r3 matrix is timing/stability evidence,
  with the p3 2048 sample linked above for eyeball only)
- Prompts outside the frozen 3-prompt × 3-seed set
- Other GPUs / stacks

## K. Non-binding AI observations (NOT a verdict)

- The p2/p3 medians (0.011/0.014) are inside the same band where phase-3
  int8-TE was independently judged 无感 by both the owner and the AI second
  opinion.
- p1's 0.058 median is consistent with "conditioning-sensitive scene +
  int8 TE", the same mechanism family as phase-3 e2-int8-te (p1 median
  0.023 at 40-step; the turbo 8-step schedule leaves less averaging, so a
  somewhat larger value is expected).
- No LPIPS value in this grid approaches the rejected w4a8 band (0.41).

*These observations describe instrument readings and prior precedent only.
The tier call is the owner's.*

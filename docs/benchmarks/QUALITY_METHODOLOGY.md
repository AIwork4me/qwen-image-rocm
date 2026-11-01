# Quality evaluation methodology

How this repo decides an optimization "didn't break the pictures" — and what
each piece of evidence does and does not mean.

## Instruments

| Instrument | What it measures | What it does NOT measure |
|---|---|---|
| **LPIPS (fidelity mode)** | perceptual distance between two images that *should* be near-identical (same model, same seed, one lever changed) | absolute quality; a 0.02 score is not "98% quality" |
| **LPIPS (distance mode)** | how *different* an intentionally-different output is (Turbo 8-step vs 40-step, ck numerics path) | whether the new image is worse — that is a human call on the grid |
| **Paired quality grids** (256 px side-by-side, per prompt × seed) | human-comparable A/B evidence at a glance | fine text quality (256 px cells hide glyph errors) |
| **Native-resolution poster crops** | text rendering at full resolution for the typography prompt | scene-level composition |
| **Determinism noise floor** | same-config rerun LPIPS (measured **0.0000** + SHA256 equality) — the yardstick below which scores are numerical noise | — |
| **Human three-tier verdict** (无感 / 略降 / 不可接受) | the binding quality decision, made by the project owner on the grids/crops | anything beyond the assessed samples |
| **AI second opinion** (GLM-5.3-Flash, frozen prompt) | an independent re-read of the same pairs; divergence ≥1 grade would reopen the gate | a replacement for the human verdict |

## The two LPIPS semantics (do not mix them)

- **fidelity** — paired images should be identical; score = damage of the
  lever. Observed bands: int8 DiT/TE 0.004–0.060 (near-lossless),
  w4a8 TE up to 0.413 (rejected), pure VRAM/cache levers 0.0000
  (bit-identical, no review needed).
- **distance** — paired images are *expected* to differ (different schedule
  or numerics path). A score of 0.21–0.36 does **not** mean "30% worse"; it
  is only the trigger for a human grid verdict. Turbo-int8+ck was judged
  无感 (A1), Turbo-bf16 and ck-40 additionally rated best-in-class (A3/A4).

**Forbidden inferences:** "LPIPS low ⇒ high quality" (it is a *distance*,
not a quality score), "human saw no difference ⇒ all users get identical
output" (verdicts describe the assessed 3-prompt × 3-seed frozen set only),
and any quality claim about prompts never run.

## Coverage today

Assessed dimensions: perceptual fidelity ✅ · paired-distance triage ✅ ·
human preference ✅ (three-tier) · text-rendering ✅ for Chinese+English
typography at native resolution (glyph-checked, including the suspected
"30H" false alarm resolved as a thumbnail artifact) · structural consistency
✅ at the "same composition" level via grids · resolution-specific quality
✅ 1024² grids + 2048² native crops (poster crops at 2048 are produced by
the probe workflow).

Not yet instrumented (explicitly): automated text-accuracy scoring (e.g.
OCR-based), artifact detectors, per-region metrics. If added, they run as
**auxiliary** evidence only.

## Frozen benchmark vs new test sets

The benchmark prompt set (3 prompts: zh scene, en scene, zh typography
poster; seeds 42/1337/20261030) is **frozen** — historical numbers must stay
comparable. A broader representative set (product photography, portraits,
multi-object composition, fine texture, complex lighting, long English
prompts) is future work and would be a **separate, clearly-labeled** suite;
it never retroactively redefines the frozen baseline.

## Verdict ledger (what has actually been decided)

- Phase 3 levers: A1 turbo-int8+ck 无感 · A2 turbo-int8 无感 · A3 turbo-bf16
  无感 (best-in-class) · A4 ck-40 无感 (best-in-class) · A5 w4a8 略降 →
  **rejected**. B1–B3 near-noise items 无感. AI second opinion: 5/5 match +
  3 first verdicts, 0 divergence ≥1 grade (`bench/results/AI_JUDGE_RESULTS.json`).
- **This session (2026-11-01):** the full production triple
  (`p3-turbo-int8-ck-te-nosmart`) has **objective evidence only** — LPIPS
  fidelity vs the already-judged e8 config: 0.058 / 0.012 / 0.014 (median,
  p1/p2/p3), max 0.075, inside the int8 near-lossless band. Grid +
  native-res crops are committed at `bench/results/2026-11-01-r1-triple/`.
  The **formal three-tier verdict on this exact grid is PENDING** (owner
  review); until then public text says "LPIPS-gated, user verdict pending",
  not 无感.

## Rules for calling something PASS

1. Objective gate computed on the frozen pairs (LPIPS with the correct
   semantics + noise floor) — recorded in `quality.md`.
2. Human verdict recorded for anything in distance semantics or with
   max-LPIPS above the near-lossless band.
3. No PASS is ever inferred from speed alone, from a single image, or from
   an unrun prompt.

# DRAFT issue — huggingface/accelerate (finding #4)

**POSTED 2026-11-01 (user-approved):** https://github.com/huggingface/accelerate/issues/4488

Target: https://github.com/huggingface/accelerate (new issue)
Channel: issue (data point + doc suggestion). User posts or authorizes gh.

---

## `enable_model_cpu_offload()`: first post-load generation thrashes the
Windows pagefile (~6x step time), silently recovers on the next run

**Environment:** Windows 11 26300, 32 GB RAM (31.8 usable), pagefile
system-managed (grew to ~55 GB cap, ~20 GB in use at observation), RX 7900
XTX 24 GB, torch 2.12.0+rocm7.14.1, accelerate 1.15.0, diffusers
QwenImage21Pipeline with `enable_model_cpu_offload()` (weights total
30.86 GB host-side: 7B DiT + 8B text encoder + VAE, bf16).

**Measured (fixed seed/protocol, median per run):**

| run (back-to-back, same process config) | steady s/step @1024² |
|---|---|
| cold (first load; OS file cache hot) | 3.6–3.7 |
| **warmup run immediately after** | **24–26 (6-7x slower)** |
| measure run right after that | 3.66 (fully recovered) |

During the slow run the pagefile grew by ~20 GB. Interpretation: with
weights ≈ system RAM, the first post-load generation forces Windows to
commit/grow the pagefile while `cpu_offload` streams module weights;
the growth cost lands on that run's steps. Steady state has no per-step
paging (DiT stays resident in VRAM; only text-encoder transfers per
prompt). It self-recovers, so it is not a correctness bug — but for other
~32 GB-RAM Windows users the symptom ("first image after loading is
~6x slower, then everything is fine") is alarming and underdocumented.

**Ask:**

1. A note in the `cpu_offload` docs: on Windows hosts where total weights
   approach system RAM, expect one sacrificial slow generation after the
   first load (pagefile commit), recovering on subsequent runs.
2. (Stretch) Consider an explicit `torch.cuda.empty_cache()`-style hint
   or a warning when `total_weights_bytes > 0.8 * total_ram` that the
   first run may page-thrash, so benchmarks discard it.

Raw protocol data: 40-step runs, median-of-3 per run class
([bench evidence](https://github.com/AIwork4me/qwen-image-rocm/blob/main/docs/issues/2026-10-30-warmup-pagefile-thrash-cpu-offload.md)).

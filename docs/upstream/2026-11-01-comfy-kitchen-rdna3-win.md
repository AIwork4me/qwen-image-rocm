# DRAFT — comfy-kitchen / ComfyUI RDNA3-Windows attention perf data point

Target: comfyanonymous/ComfyUI discussion (perf data), or comfy-kitchen
repo issue if maintainers prefer. Channel: discussion post; user posts or
authorizes gh.

---

## Windows/RDNA3 data point: `--use-ck-attention` (comfy-kitchen 0.2.40)
## is 1.30–1.37x vs default attention at 1024² (Qwen-Image-2.1)

There is no public Windows-RDNA3 benchmark for the Comfy Kitchen HIP
attention backends that I could find, so here is a reproducible one.

**Setup:** Windows 11 26300, RX 7900 XTX 24 GB (gfx1100), driver
32.0.21030.2001, torch 2.12.0+rocm7.14.1 (repo.amd.com whl-multi-arch),
ComfyUI 0.43.0 (b5a4321), comfy-kitchen 0.2.40 (PyPI), Qwen-Image-2.1
bf16 (Comfy-Org split), 40 steps, 3 prompts (zh scene / en scene / poster
text), fixed seeds, n=9 per variant, server fully restarted per variant
(protocol v1.3: websocket node/step timing, true VRAM peak).

**Result (median s/image @1024², 40 steps):**

| attention | p1 | p2 | p3 | speedup vs default | VRAM peak |
|---|---|---|---|---|---|
| default (flash auto-disabled at startup probe → sub-quadratic) | 48.4 | 51.5 | 47.4 | 1.00x | 17.7 GB |
| `--use-ck-attention` | 35.2 | 37.5 | 37.3 | **1.37x / 1.34x / 1.30x** | 17.0 GB |

Context for readers on the broken-flash Windows builds
(TheRock#7315 family): on this stack torch's flash/mem-efficient SDPA
fails at launch (`hipErrorInvalidValue`), so "default" already means
ComfyUI's fallback path — ck is not beating flash here, it is beating the
fallback. ck's HIP kernels bypass torch SDPA dispatch entirely, which is
also independent evidence the GPU itself handles these attention shapes
fine.

For calibration with AMD's published numbers: the Linux composable_kernel
blog (WAN2.2, Navi31) reports +31.6–36.4% vs AOTriton SDPA — a different
implementation (composable_kernel vs Comfy Kitchen's HIP int8 path), but
numerically consistent with the 1.30–1.37x we see on Windows/RDNA3.

Combines multiplicatively with Turbo-8-step + native int8 checkpoints:
our measured best 1024² config (turbo + int8 DiT/TE + ck) is
**5.2–5.5x** vs the bf16-40-step baseline (48 s → 9.1 s), image quality
gated (LPIPS + human + independent AI second-opinion, 0 divergence).

Full protocol, per-run JSON, LPIPS tables, and the 192-cell SDPA matrix
that documents why default falls back:
[bench/results](https://github.com/AIwork4me/qwen-image-rocm/tree/main/bench/results)
(phase3 summary report).

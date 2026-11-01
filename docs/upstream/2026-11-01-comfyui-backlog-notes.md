# DRAFT backlog notes — comfyanonymous/ComfyUI (optional, only if time)

**POSTED 2026-11-01 (user-approved) as two ComfyUI issues:** VAEDecodeTiled https://github.com/Comfy-Org/ComfyUI/issues/17469 · fp16_accumulation https://github.com/Comfy-Org/ComfyUI/issues/17470

Two Windows-ROCm-observed behaviors worth upstream issues if maintainers
agree they are actionable. Lower priority than items 1–5 (user may skip).

## A. VAEDecodeTiled residency thrash at 1024² (5x slower, not memory-bound)

`VAEDecodeTiled` at 1024² on a 24 GB card with the DiT + TE resident
measured **5.53 s/step median (244.8 s/image) vs ~1 s/step** for the
non-tiled decode — ~5x slower — with VRAM peak *rising* to 21.8 GB.
Interpretation: tiled decode keeps the VAE resident across many tile
iterations, which evicts the next model in the cache chain; the following
step re-streams weights (residency thrash), so the "memory-saving" node
costs 5x time and more peak memory in the mid-VRAM regime where the
non-tiled decode fits anyway. A doc note ("use tiled decode only when the
non-tiled decode OOMs") or an eviction-aware cache hint might save users
a confusing 5x regression.
Evidence: `bench/results/2026-11-01-e6-vaetiled-v2/` (n=5).

## B. `--fast fp16_accumulation` long-text pathology (0.22x on poster prompt)

With `--fast fp16_accumulation`, the text-heavy poster prompt (p3,
141 chars) runs at **223.7 s vs 47.4 s** control (0.22x) while the two
scene prompts are ~parity (1.02x/1.04x). Same stack as above; n=15.
Consistent with an fp16-accumulation pathological kernel for long TE
sequences on RDNA3 Windows; flagging in case maintainers want the shape
for a kernel fix (we can provide the isolated prompt + timings; the TE
here is Qwen3-VL 8B, GQA 32Q/8KV, head_dim 128).
Evidence: `bench/results/2026-11-01-e7-fp16acc/`.

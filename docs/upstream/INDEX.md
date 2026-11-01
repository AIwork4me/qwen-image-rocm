# Upstream contribution drafts — Phase 4 (ALL user-gated)

Nothing here is posted. Each draft names its target and submit channel.
Approval list for the user is at the bottom; posted links get recorded back
into the individual files after the user approves and (optionally) posts.

| # | file | target | channel | status |
|---|---|---|---|---|
| 1 | [therock-7315-comment.md](2026-11-01-therock-7315-comment.md) | ROCm/TheRock#7315 | comment (user posts personally as AMD employee, or authorizes gh) | DRAFT |
| 2 | [transformers-diffusers-sdpa-resilience.md](2026-11-01-transformers-diffusers-sdpa-resilience.md) | huggingface/transformers + diffusers | issue first, then PR | DRAFT |
| 3 | [accelerate-pagefile-thrash.md](2026-11-01-accelerate-pagefile-thrash.md) | huggingface/accelerate | issue | DRAFT |
| 4 | [hfhub-4196-comment.md](2026-11-01-hfhub-4196-comment.md) | huggingface_hub#4196 | comment | DRAFT |
| 5 | [comfy-kitchen-rdna3-win.md](2026-11-01-comfy-kitchen-rdna3-win.md) | comfyanonymous/ComfyUI discussion (or comfy-kitchen repo issue) | discussion/issue | DRAFT |
| 6 | [comfyui-backlog-notes.md](2026-11-01-comfyui-backlog-notes.md) | comfyanonymous/ComfyUI | issues (optional backlog) | DRAFT |

## Approval checklist (one page)

Approve per item; "user posts" = you post personally (AMD identity);
"AI posts" = authorize gh submission from this repo's CLI (AIwork4me):

- [ ] 1. TheRock#7315 comment — user posts / AI posts / skip
- [ ] 2. transformers+diffusers SDPA resilience issue — user posts / AI posts / skip
- [ ] 3. accelerate pagefile-thrash issue — user posts / AI posts / skip
- [ ] 4. hf#4196 comment — user posts / AI posts / skip
- [ ] 5. comfy-kitchen RDNA3/Windows data point — user posts / AI posts / skip
- [ ] 6. ComfyUI backlog notes (VAEDecodeTiled thrash, fp16_accumulation) — user posts / AI posts / skip

Cross-post hygiene: item 1 optionally cross-references ROCm/aotriton#210
(one line, same content). Item 2 links #7315 as root cause, not a dup.

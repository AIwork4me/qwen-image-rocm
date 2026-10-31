# Quality gate — p3-turbo-int8-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e2-turbo-int8`
- LPIPS semantics: DISTANCE, NOT QUALITY — a different model/schedule (Turbo) legitimately produces different images; a high score does not mean worse. The three-tier verdict is the user's 目检 call on the grid.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.3524 | 0.3805 | 3 |
| p2-en-scene | 0.2218 | 0.2872 | 3 |
| p3-poster-text | 0.2599 | 0.2618 | 3 |

## Verdict (user final — 三档终审)

- [ ] 无感 (imperceptible)
- [ ] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: 

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

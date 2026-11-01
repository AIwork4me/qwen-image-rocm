# Quality gate — p3-turbo-8step-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e1-turbo`
- LPIPS semantics: DISTANCE, NOT QUALITY — a different model/schedule (Turbo) legitimately produces different images; a high score does not mean worse. The three-tier verdict is the user's 目检 call on the grid.
- LPIPS noise floor (same-config determinism): **0.0000** — differences below this are noise.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.2791 | 0.3405 | 3 |
| p2-en-scene | 0.1948 | 0.3058 | 3 |
| p3-poster-text | 0.2628 | 0.2715 | 3 |

## Verdict (user final — 三档终审)

- [x] 无感 (imperceptible)
- [ ] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: user 2026-11-01: A3 几乎无感，用户评价优于 A1/A2 → 均衡推荐

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

## AI 复审 (GLM-5.3-Flash, 2026-11-01)

- AI verdict: **无感**（9 对 worst-case，confidence 0.9）
- 与人工终审一致: 是（人工 无感（更优） / AI 无感，差 0 档）
- Key evidence:
  - 9 对无伪影；p2-r1 hiker 主体呈现、p1-r2 桥拱过曝处理优于基线
  - 文字 3 种子全部正确
  - 支持人工档『无感（更优）』：多个 pair 存在可见更优局部，无任何 pair 劣于基线
- LPIPS 一致性: 与 LPIPS 0.28/0.19/0.26 一致。与人工终审『无感（更优）』一致，差 0 档。
- 文字验证: seed42 依据 `quality_crops_poster.png`；seed1337/20261030 依据 `results/raw` 原生分辨率副标题核验（缩略图『30H』为 256px 伪影，原生分辨率下全部为正确『日』，无错字/缺画/乱码）
- 逐对明细 (9 pairs JSON): `../AI_JUDGE_RESULTS.json` → experiments[A3]

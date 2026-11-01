# Quality gate — p3-e4-ck-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e4-ck`
- LPIPS semantics: FIDELITY — same model, same seed, only the numerics path changed (quantization / attention backend). Lower = closer to the bf16 reference; compare against the noise floor before reading anything into small values.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.3418 | 0.4494 | 3 |
| p2-en-scene | 0.2150 | 0.2279 | 3 |
| p3-poster-text | 0.0696 | 0.1076 | 3 |

## Verdict (user final — 三档终审)

- [x] 无感 (imperceptible)
- [ ] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: user 2026-11-01: A4 几乎无感，与 A3 并列最佳 → 最高质量推荐

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

## AI 复审 (GLM-5.3-Flash, 2026-11-01)

- AI verdict: **无感**（9 对 worst-case，confidence 0.85）
- 与人工终审一致: 是（人工 无感（更优） / AI 无感，差 0 档）
- Key evidence:
  - 9 对无伪影；p2-r0 hiker 主体、p3-r0 飞船细节优于基线
  - 文字 3 种子全部正确
  - p3-r2 实验飞船几乎融入星云——内容差异（类型B预期）不计缺陷
- LPIPS 一致性: 与 LPIPS 0.34/0.22/0.07 一致。与人工终审『无感（更优）』一致，差 0 档。
- 文字验证: seed42 依据 `quality_crops_poster.png`；seed1337/20261030 依据 `results/raw` 原生分辨率副标题核验（缩略图『30H』为 256px 伪影，原生分辨率下全部为正确『日』，无错字/缺画/乱码）
- 逐对明细 (9 pairs JSON): `../AI_JUDGE_RESULTS.json` → experiments[A4]

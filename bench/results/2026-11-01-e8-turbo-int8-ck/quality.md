# Quality gate — p3-turbo-int8-ck-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e8-turbo-int8-ck`
- LPIPS semantics: DISTANCE, NOT QUALITY — a different model/schedule (Turbo) legitimately produces different images; a high score does not mean worse. The three-tier verdict is the user's 目检 call on the grid.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.3605 | 0.4157 | 3 |
| p2-en-scene | 0.2661 | 0.3010 | 3 |
| p3-poster-text | 0.2059 | 0.2631 | 3 |

## Verdict (user final — 三档终审)

- [x] 无感 (imperceptible)
- [ ] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: user 2026-11-01: A1 几乎无感（A3/A4 相对更优）；推荐极速配置

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

## AI 复审 (GLM-5.3-Flash, 2026-11-01)

- AI verdict: **无感**（9 对 worst-case，confidence 0.85）
- 与人工终审一致: 是（人工 无感 / AI 无感，差 0 档）
- Key evidence:
  - 9 对均无伪影/结构崩坏/细节涂抹（256px 网格全检）
  - 文字 3 种子全部正确；grid 缩略图 p3-r1 疑似『30H』经 raw 原生分辨率排除为缩略伪影
  - p1-r2 基线太阳过曝，实验反而更柔——存在优于基线的局部
- LPIPS 一致性: 与 LPIPS 0.36/0.27/0.21 一致：跨模型大差异为预期（类型A），LPIPS 测差异不测质量，质量级判定为同级。与人工终审『无感』一致，差 0 档。
- 文字验证: seed42 依据 `quality_crops_poster.png`；seed1337/20261030 依据 `results/raw` 原生分辨率副标题核验（缩略图『30H』为 256px 伪影，原生分辨率下全部为正确『日』，无错字/缺画/乱码）
- 逐对明细 (9 pairs JSON): `../AI_JUDGE_RESULTS.json` → experiments[A1]

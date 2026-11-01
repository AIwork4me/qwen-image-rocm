# Quality gate — p3-int8-te-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e2-int8-te`
- LPIPS semantics: FIDELITY — same model, same seed, only the numerics path changed (quantization / attention backend). Lower = closer to the bf16 reference; compare against the noise floor before reading anything into small values.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.0228 | 0.0602 | 3 |
| p2-en-scene | 0.0158 | 0.0242 | 3 |
| p3-poster-text | 0.0035 | 0.0181 | 3 |

## Verdict (user final — 三档终审)

- [ ] 无感 (imperceptible)
- [ ] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: 

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

## AI 复审 (GLM-5.3-Flash, 2026-11-01)

- AI verdict: **无感**（9 对 worst-case，confidence 0.9）
- 与人工终审一致: 未终审（AI 首判，建议归档）
- Key evidence:
  - 9 对近逐像素一致
  - 文字 3 种子正确（裁剪图+raw）
  - 支持 int8 TE 作为 w4a8 替代（A5）的画质依据
- LPIPS 一致性: 与 LPIPS 0.02/0.02/0.004（近噪声底）一致。人工未终审，AI 首判无感，建议直接归档。
- 文字验证: seed42 依据 `quality_crops_poster.png`；seed1337/20261030 依据 `results/raw` 原生分辨率副标题核验（缩略图『30H』为 256px 伪影，原生分辨率下全部为正确『日』，无错字/缺画/乱码）
- 逐对明细 (9 pairs JSON): `../AI_JUDGE_RESULTS.json` → experiments[B2]

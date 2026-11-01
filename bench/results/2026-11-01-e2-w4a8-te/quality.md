# Quality gate — p3-w4a8-te-1024x1024

- Baseline: `results/raw/2026-10-31-e1-control` (bf16, 40 steps)
- Experiment: `results/raw/2026-11-01-e2-w4a8-te`
- LPIPS semantics: FIDELITY — same model, same seed, only the numerics path changed (quantization / attention backend). Lower = closer to the bf16 reference; compare against the noise floor before reading anything into small values.

| Prompt | median LPIPS | max LPIPS | n pairs |
|---|---|---|---|
| p1-zh-scene | 0.1888 | 0.4127 | 3 |
| p2-en-scene | 0.0872 | 0.1434 | 3 |
| p3-poster-text | 0.0426 | 0.0661 | 3 |

## Verdict (user final — 三档终审)

- [ ] 无感 (imperceptible)
- [x] 略降 (slightly degraded)
- [ ] 不可接受 (unacceptable)

Notes: user 2026-11-01: A5 略降 → w4a8 拒绝，int8 TE 为替代

Grids: `quality_grid.png` (256px pairs), `quality_crops_poster.png` (native-res text crops, poster prompt).

## AI 复审 (GLM-5.3-Flash, 2026-11-01)

- AI verdict: **略降**（9 对 worst-case，confidence 0.7）
- 与人工终审一致: 是（人工 略降 / AI 略降，差 0 档）
- Key evidence:
  - 类型C应『几乎相同』，p1-r0 构图大幅偏移+色调单调化、p2-r0/p2-r2 first light 弱化与云雾吞山——同种子可复现性被破坏且存在质量性让步方向
  - p3 行（LPIPS 0.04）高度保真：文字/版面/飞船与基线一致
  - 无伪影/结构崩坏/文字错乱——不到『不可接受』
- LPIPS 一致性: 与 LPIPS 一致：p1 中位 0.19/max 0.41 对应构图级漂移，p3 0.04 对应近一致。与人工终审『略降（w4a8 拒绝）』一致，差 0 档；支持以 int8 TE 替代（B2 LPIPS 0.02 且本审无感）。
- 文字验证: seed42 依据 `quality_crops_poster.png`；seed1337/20261030 依据 `results/raw` 原生分辨率副标题核验（缩略图『30H』为 256px 伪影，原生分辨率下全部为正确『日』，无错字/缺画/乱码）
- 逐对明细 (9 pairs JSON): `../AI_JUDGE_RESULTS.json` → experiments[A5]

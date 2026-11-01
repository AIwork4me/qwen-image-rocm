# Contributing to qwen-image-rocm

Thanks for your interest! This project benchmarks and optimizes
Qwen-Image-2.1 image generation on AMD RDNA3 GPUs (Radeon 7900 XTX) under
Windows-native ROCm — with evidence discipline: every measured claim points
at a committed run record.

## Getting started

- Read the [README](README.md) for the 60-second picture, then
  [`docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md`](docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md)
  for how claims are justified, and
  [`bench/prompts.json`](bench/prompts.json) for the frozen protocol.
- `.\quickstart.ps1 -Mode Fast` sets up everything and generates a first
  image; `reproduce.ps1` covers the Phase-1 diffusers baseline.

## Running the tests (no GPU needed)

```
uv run --with pytest --with jsonschema --with matplotlib --with pillow --with numpy --with requests pytest tests/ -v
uv run --with ruff ruff check .
```

This is exactly what the CPU CI gate runs. GPU validation is a separate
manual, self-hosted workflow (`.github/workflows/gpu-validation.yml`) — a
GitHub-hosted runner has no Radeon and is never claimed as GPU-verified.

## Making changes

- Conventional commits (`feat:`, `fix:`, `docs:`, `data:`, `chore:`); keep
  them atomic.
- **Never edit anything under `bench/results/`** — history is read-only.
  New runs go into new directories (`run_variant.ps1` does this for you).
- New performance/quality claims must land with their records and a row in
  the claim matrix; PRs without evidence get downgraded or bounced.
- README.md and README.zh-CN.md are mirrors — update both.
- Scan any committed log output for secrets first:
  `grep -riEl 'ghp_|gho_|hf_[A-Za-z0-9]{20}|api[_-]?key|password|authorization:|secret' <dir>`

## Reporting issues

Use the issue templates. Bug reports need the output of
`python -I tools\snapshot_env.py` and complete error text (not screenshots).
ROCm-on-Windows problems are triaged in `docs/issues/` first, then posted
upstream with links. GPU reports from untested cards are welcome and feed
the community support matrix (CC-BY-4.0 with attribution to you).

# Contributing to qwen-image-rocm

Thanks for your interest! This project benchmarks and optimizes
Qwen-Image-2.1 image generation on AMD RDNA3 GPUs (Radeon 7900 XTX) under
Windows-native ROCm.

## Getting started

- Read `docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md` for the
  project design and `bench/prompts.json` for the frozen benchmark protocol.
- `reproduce.ps1` sets up a full environment from scratch (see README).

## Running the tests

```
uv run --with pytest --with jsonschema --with matplotlib --with ruff --with requests pytest tests/ -v
```

No GPU is required for the test suite; GPU-dependent scripts under
`phase1-diffusers/` are verified separately.

## Commit style

Conventional commits (`feat:`, `fix:`, `docs:`, `data:`, `chore:`). Keep
commits atomic.

## Reporting issues

Include: full environment info (output of `tools/snapshot_env.py`), complete
error output as text (not screenshots), and a minimal reproducer. Issues
related to ROCm on Windows are triaged in `docs/issues/`.

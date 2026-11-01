<!-- Thanks! PRs that change measured claims must point at evidence records. -->

## What & why

<!-- user-facing summary; link the issue if any -->

## Evidence

<!-- For perf/quality claims: which run records (bench/results/<dir>) back
     the numbers in this PR? For code-only changes: which tests cover it?
     Claims without records get downgraded per docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md -->

- [ ] New/changed claims resolve to committed run records (or are marked PROJECTED/UNVERIFIED)

## Checklist

- [ ] `uv run --with pytest --with jsonschema --with matplotlib --with pillow --with numpy --with requests pytest tests/ -v` green (CPU gate)
- [ ] `uv run --with ruff ruff check .` clean
- [ ] No model weights or secrets in the diff (`git diff --stat` reviewed; new logs scanned)
- [ ] Historical `bench/results/` untouched (new runs go in new directories)
- [ ] README.md and README.zh-CN.md updated in sync (if user-facing)

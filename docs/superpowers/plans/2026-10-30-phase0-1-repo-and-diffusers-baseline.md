# qwen-image-rocm Phase 0+1: Repo & Diffusers Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the open-source repo `AIwork4me/qwen-image-rocm` and produce a verified, reproducible diffusers text-to-image baseline for Qwen-Image-2.1 on Windows ROCm (7900 XTX), with benchmark data committed as evidence.

**Architecture:** Single git repo at `C:\Users\Rocm\Desktop\image` (remote name `qwen-image-rocm`). A frozen benchmark protocol (`bench/`) drives a generation CLI (`phase1-diffusers/generate.py`) inside a uv-managed venv running AMD ROCm wheels. Pure-logic pieces (prompt set, result schema, report) are pytest-tested; GPU runs are verification-step-checked. Issues found are logged to `docs/issues/`, never fixed inline.

**Tech Stack:** Python 3.12 (fallback per AMD wheels), uv + pip, torch 2.12.0+rocm7.14.1 (gfx1100 wheels, mandated command verbatim), diffusers `QwenImage21Pipeline`, transformers ≥5.17, modelscope CLI, pytest, ruff, matplotlib (Agg), GitHub Actions.

**Spec:** `docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md`

**Scope:** Phase 0 + Phase 1 only. Phase 2 (ComfyUI), Phase 3 (optimization), Phase 4 (upstream RCA/PR) each get their own plan at their milestone.

## Global Constraints

- Windows native; GPU 7900 XTX (gfx1100), driver 32.0.21030.2001. No WSL.
- torch install command, verbatim, nothing else may install torch: `python -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1100]==2.12.0+rocm7.14.1" "torchvision[device-gfx1100]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"`
- Model weights only from ModelScope (`Qwen/Qwen-Image-2.1`).
- This session's shell predates git/gh install: use absolute paths `"C:\Program Files\Git\cmd\git.exe"` and `"C:\Program Files\GitHub CLI\gh.exe"` (plain names work after ZCode restart).
- gitignore: `weights/`, `**/.venv/`, `phase2-comfyui/ComfyUI/`, `results/raw/`. Image pushes ≤100MB (curated grids + samples only).
- Upstream-facing artifacts (issues, PRs, RCA docs) in English; repo working notes may be Chinese.
- Baseline venv is frozen once verified: no package changes after benchmark data is collected.
- ROCm problems during Phase 0–1: log to `docs/issues/YYYY-MM-DD-<slug>.md` (env, full error text, suspected layer). Only minimal workarounds for hard blockers, themselves logged. No fixes.
- Commits after every task; push after every task.
- Repo content dual license: code MIT (`LICENSE`), benchmark data CC-BY-4.0 (noted in README + `docs/DATA_LICENSE.md`).

## Review Focus

- **Silent CPU fallback** (torch not seeing HIP) would produce valid-but-slow images. `smoke_hip.py` exits nonzero unless `torch.cuda.is_available()` and device reports gfx1100; `generate.py` asserts the same before loading the pipeline. Pinned in Tasks 4, 6.
- **pip swapping ROCm torch for a PyPI build** when other deps install. After every `pip install`, a check step asserts `torch.__version__.endswith("rocm7.14.1")`. Pinned in Tasks 4, 6.
- **Prompts edited after baselines exist** invalidates all comparisons. `test_prompts.py` asserts the exact three ids and a content hash. Pinned in Task 2.
- **Malformed result JSON** breaks report generation and cross-phase comparison. Harness validates each result against the schema before writing; schema itself round-trip tested. Pinned in Tasks 2, 7.
- **Timer catching model load in warm runs** inflates medians. `run_bench.py` separates cold (first load, recorded once per process) from warm runs in its pure `plan_runs()` logic, unit-tested. Pinned in Task 7.

---

### Task 1: Repo scaffold + GitHub remote (Phase 0)

**Files:**
- Create: `.gitignore`, `README.md`, `README.zh-CN.md`, `LICENSE`, `docs/DATA_LICENSE.md`, `CONTRIBUTING.md`, `docs/issues/.gitkeep`
- Uses existing: `docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md`

**Interfaces:**
- Produces: git repo with remote `origin` = `AIwork4me/qwen-image-rocm` (public), default branch `main`.

- [ ] **Step 1: Install uv**

Run: `winget install --id=astral-sh.uv -e` then `uv --version` in a fresh shell (uv installs to user PATH; if not visible this session, use full path `%USERPROFILE%\.local\bin\uv.exe`).
Expected: a version line like `uv 0.x.y`.

- [ ] **Step 2: Init repo and write scaffold files**

Run: `"C:\Program Files\Git\cmd\git.exe" init -b main` in `C:\Users\Rocm\Desktop\image`.
`.gitignore` lines (exact): `weights/`, `**/.venv/`, `__pycache__/`, `*.pyc`, `phase2-comfyui/ComfyUI/`, `results/raw/`, `.pytest_cache/`, `.ruff_cache/`, `modelscope_cache/`.
`README.md`: project title qwen-image-rocm, one-paragraph mission (English), status "Phase 1 in progress", link to spec, dual-license note, setup section left as TODO placeholder.
`README.zh-CN.md`: Chinese mirror of the same.
`LICENSE`: MIT, copyright 2026 AIwork4me.
`docs/DATA_LICENSE.md`: one line "Benchmark data and reports in bench/results/ are licensed CC-BY-4.0" plus CC-BY-4.0 URL.
`CONTRIBUTING.md`: short English stub (how to run tests, commit style conventional, issue expectations).

- [ ] **Step 3: Create remote and first push**

Run: `"C:\Program Files\Git\cmd\git.exe" add -A` ; commit `chore: scaffold qwen-image-rocm repo (phase 0)` (set `user.name`/`user.email` via `git config` first if unset — ask user which identity if unknown); `"C:\Program Files\GitHub CLI\gh.exe" repo create qwen-image-rocm --public --source . --remote origin --push`.
Expected: repo created, `gh repo view --web` unnecessary; verify with `gh repo view AIwork4me/qwen-image-rocm --json name,visibility` returning `"visibility": "PUBLIC"`.

### Task 2: Benchmark protocol skeleton — prompts, result schema, CI (TDD)

**Files:**
- Create: `bench/prompts.json`, `bench/schema/result.schema.json`, `tests/test_prompts.py`, `tests/test_result_schema.py`, `.github/workflows/ci.yml`, `pyproject.toml` (pytest+ruff config only, no deps)
- Test: `tests/test_prompts.py`, `tests/test_result_schema.py`

**Interfaces:**
- Produces: prompt ids `p1-zh-scene`, `p2-en-scene`, `p3-poster-text` (consumed by `generate.py` Task 6 and `run_bench.py` Task 7); result schema fields (below) consumed by report tooling.
- Produces: `bench/prompts.json` structure `{"protocol_version": "v1", "seeds": [42, 1337, 20261030], "prompts": [{"id": str, "prompt": str, "negative_prompt": str}, ...]}`.
- Result schema requires: `experiment: str`, `phase: int`, `framework: str`, `precision: str`, `width: int`, `height: int`, `steps: int`, `seed: int`, `prompt_id: str`, `protocol_version: str`, `runs: [{"kind": "cold"|"warm", "total_s": number, "text_encode_s": number|null, "denoise_s": number, "vae_decode_s": number|null, "step_times_s": [number]}]`, `vram_peak_mb: number`, `env_ref: str`, `created_at: str (ISO 8601)`. Additional properties allowed.

- [ ] **Step 1: Write failing tests**

`tests/test_prompts.py`:
```python
import json, hashlib
def load():
    return json.load(open("bench/prompts.json", encoding="utf-8"))

def test_protocol_frozen():
    d = load()
    assert d["protocol_version"] == "v1"
    assert d["seeds"] == [42, 1337, 20261030]

def test_exactly_three_prompts_with_frozen_ids_and_text():
    d = load()
    assert [p["id"] for p in d["prompts"]] == ["p1-zh-scene", "p2-en-scene", "p3-poster-text"]
    h = hashlib.sha256(json.dumps(d["prompts"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert h == PROMPT_SET_SHA256  # filled in Step 3 after writing the file once; then frozen
```
`tests/test_result_schema.py`: `test_schema_validates_good_sample` (sample dict with all fields above passes `jsonschema.validate`), `test_schema_rejects_missing_seed` (validation error raised).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with jsonschema pytest tests/ -v` (no venv exists yet; uv ephemeral env runs tests).
Expected: FAIL — `FileNotFoundError` for `bench/prompts.json` (schema test fails similarly).

- [ ] **Step 3: Write `bench/prompts.json` and `bench/schema/result.schema.json`**

Prompt texts (exact copy, then compute `PROMPT_SET_SHA256` and paste into the test — one-shot, this freezes the protocol):
- `p1-zh-scene`: "夕阳下的江南水乡小镇，石桥横跨河道，乌篷船缓缓驶过，白墙黛瓦的民居倒映在金色的河面上，远处炊烟袅袅，超高清摄影质感"
- `p2-en-scene`: "A lone hiker standing on a mountain ridge at dawn, a sea of clouds below, first light hitting the peaks, ultra-detailed landscape photography"
- `p3-poster-text`: "电影海报设计，主标题文字「星际远航」，副标题文字「2026年10月30日 全球上映」，画面是深空中的巨型飞船与绚丽星云，标题文字清晰锐利、排版居中"
- all `negative_prompt`: ""
Schema: JSON Schema draft 2020-12 object implementing the Interfaces block above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with jsonschema pytest tests/ -v`
Expected: PASS (4 tests).

- [ ] **Step 5: CI workflow**

`.github/workflows/ci.yml`: on push/PR; ubuntu-latest; setup-python 3.12; `uv run --with pytest --with jsonschema --with ruff pytest tests/ -v`; `uv run --with ruff ruff check .`.

- [ ] **Step 6: Commit and push**

`git add bench/ tests/ .github/ pyproject.toml` ; commit `feat(bench): freeze benchmark protocol v1 (prompts, seeds, result schema) + CI`.

### Task 3: Environment snapshot tool (TDD)

**Files:**
- Create: `tools/snapshot_env.py`, `tests/test_env_snapshot.py`

**Interfaces:**
- Produces: `build_snapshot(os_build: str, gpu_name: str, driver_version: str, python_version: str, torch_version: str|None, torchvision_version: str|None, hip_version: str|None, gfx_arch: str|None, created_at: str) -> dict` (pure); `collect() -> dict` (reads real system/torch; imports torch lazily, returns torch fields as None when torch absent); `main() -> None` writes `bench/results/env/snapshot-<YYYYMMDD-HHMMSS>.json` and prints the path.

- [ ] **Step 1: Write failing test**

`tests/test_env_snapshot.py`: `test_build_snapshot_fields` — all keys present, torch fields None-able, created_at ISO 8601 parses; `test_collect_without_torch` — monkeypatch `importlib.util.find_spec` to return None for torch, `collect()["torch_version"] is None` and no exception.

- [ ] **Step 2: Run, expect FAIL** — `ModuleNotFoundError: tools.snapshot_env`. Run: `uv run --with pytest --with jsonschema pytest tests/test_env_snapshot.py -v`

- [ ] **Step 3: Implement `tools/snapshot_env.py`**

GPU name/driver from `powershell Get-CimInstance Win32_VideoController` (filter `Name -like '*AMD*'`); os build from `sys.getwindowsversion()`; lazy torch import inside `collect()`.

- [ ] **Step 4: Run, expect PASS.** Same command as Step 2.

- [ ] **Step 5: Commit** — `feat(tools): environment snapshot tool`.

### Task 4: Phase 1 venv + mandated torch install + HIP smoke test

**Files:**
- Create: `phase1-diffusers/smoke_hip.py`, `phase1-diffusers/requirements.txt`, `phase1-diffusers/requirements.lock.txt`
- Create dir: `weights/` (gitignored)

**Interfaces:**
- Produces: venv at `phase1-diffusers/.venv` (Python 3.12; if the AMD index has no cp312 wheel for torch, retry with 3.11 then 3.13 — record chosen version in the issue-free commit message and README env section).
- Produces: `smoke_hip.py` — `main()` prints torch/hip/device lines, `sys.exit(1)` if `not torch.cuda.is_available()` or `"1100" not in gfx_arch`; importable parts factored as `check(torch) -> list[str]` returning problem lines.

- [ ] **Step 1: Create venv with seeded pip**

Run: `uv venv phase1-diffusers/.venv --python 3.12 --seed` (uv downloads CPython if absent).
Expected: `.venv\Scripts\python.exe` exists.

- [ ] **Step 2: Install torch with the mandated command, verbatim**

Run: `phase1-diffusers\.venv\Scripts\python.exe -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1100]==2.12.0+rocm7.14.1" "torchvision[device-gfx1100]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"`
Expected: success, multi-GB download. Any failure → `docs/issues/` entry (full log), then stop and report.

- [ ] **Step 3: Write and run `smoke_hip.py`**

Implement `check()` + `main()` as in Interfaces. Run: `phase1-diffusers\.venv\Scripts\python.exe -I phase1-diffusers\smoke_hip.py`
Expected stdout includes `torch=2.12.0+rocm7.14.1`, a hip version line, device name containing `7900 XTX` (or `Radeon RX 7900 XTX`), arch line containing `gfx1100`, exit code 0. Failures (wrong arch, missing kernel dlls) → log issue with full output; only a hard blocker gets a minimal workaround.

- [ ] **Step 4: Install remaining deps, then verify torch untouched**

`phase1-diffusers/requirements.txt` (pinned at install time to what resolves; floor values): `transformers>=5.17`, `diffusers` (latest release; if `QwenImage21Pipeline` absent, switch to `diffusers @ git+https://github.com/huggingface/diffusers` and pin the commit), `accelerate`, `pillow`, `modelscope`, `sentencepiece`, `protobuf`.
Run: `phase1-diffusers\.venv\Scripts\python.exe -m pip install -r phase1-diffusers\requirements.txt`
Then: `phase1-diffusers\.venv\Scripts\python.exe -c "import torch; assert torch.__version__.endswith('rocm7.14.1'), torch.__version__; print('torch OK', torch.__version__)"`
Expected: `torch OK 2.12.0+rocm7.14.1`. If the assert fails, pip swapped torch: reinstall via the mandated command, add `torch==2.12.0+rocm7.14.1` as a constraint line comment in requirements.txt, log an issue.

- [ ] **Step 5: Freeze lock + snapshot env**

`python -m pip freeze > phase1-diffusers\requirements.lock.txt` (committed — this replaces the design's `uv.lock`, since the mandated command is pip-based; note this in README).
Run `tools/snapshot_env.py` with the venv python; commit the snapshot JSON under `bench/results/env/`.

- [ ] **Step 6: Commit and push** — `feat(phase1): venv with rocm7.14.1 gfx1100 stack, smoke-verified; lock env`.

### Task 5: Download weights from ModelScope

**Files:**
- Create: `weights/diffusers-format/` (gitignored), `docs/weights.md` (download command + expected layout, English)

**Interfaces:**
- Produces: local weights dir loadable by `QwenImage21Pipeline.from_pretrained("weights/diffusers-format")`.

- [ ] **Step 1: Download**

Run (background, ~30GB): `phase1-diffusers\.venv\Scripts\modelscope.exe download --model Qwen/Qwen-Image-2.1 --local_dir weights\diffusers-format`
Expected: exit 0. If ModelScope auth/region errors occur, log issue; do not switch to HF without user approval.

- [ ] **Step 2: Verify layout**

Check `weights\diffusers-format` contains `model_index.json`, `tokenizer*/`, `text_encoder*/` (or Qwen3-VL equivalent dirs), `transformer*/` with `*.safetensors` shards, `vae*/`. Total size > 25GB (`dir /s` sum). Record exact file list in `docs/weights.md`.

- [ ] **Step 3: Commit** — `docs(phase1): record weight download procedure` (weights themselves never committed).

### Task 6: Generation CLI with stage timing

**Files:**
- Create: `phase1-diffusers/generate.py`, `tests/test_generate_config.py`
- Test: `tests/test_generate_config.py` (torch/diffusers NOT importable requirement — heavy imports stay inside `main()`)

**Interfaces:**
- Consumes: `bench/prompts.json` (Task 2 ids), weights path (Task 5), venv (Task 4).
- Produces: `resolve_prompt(prompt_id: str) -> tuple[str, str]` (text, negative) reading `bench/prompts.json`; `parse_args(argv: list[str]) -> argparse.Namespace` with `--prompt-id` (exclusive with `--prompt`), `--width` (default 2048), `--height` (default 2048), `--steps` (default 40), `--seed` (default 42), `--out` (default `results/raw/`), `--precision` (`bf16`, default); `main()` loads pipeline (`torch_dtype=torch.bfloat16`, `enable_model_cpu_offload()`), generates, saves `<out>/<experiment>/<seed>-<idx>.png` plus a sidecar `<...>.json` per the Task 2 schema, prints the schema JSON to stdout.
- Stage timing: per-step times via `callback_on_step_end`; text-encode / VAE-decode via component calls where `QwenImage21Pipeline` exposes them, else `null` in the sidecar with a one-line comment in the script header documenting the actual method. `denoise_s` is always real.

- [ ] **Step 1: Write failing test**

`tests/test_generate_config.py`: `test_resolve_prompt_ids` — for each of the three ids returns non-empty text and "" negative; `test_parse_args_exclusive` — `--prompt-id` and `--prompt` together → `SystemExit`; `test_defaults` — defaults are 2048/2048/40/42/bf16. Import must succeed with plain `uv run --with pytest` (no torch installed there) — hence lazy heavy imports.

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError` / `FileNotFoundError`). Run: `uv run --with pytest --with jsonschema pytest tests/test_generate_config.py -v`

- [ ] **Step 3: Implement `generate.py`**

Per Interfaces. Assert `torch.cuda.is_available()` and gfx1100 before pipeline load (reuse `smoke_hip.check`). `experiment` name pattern: `p1-bf16-<width>x<height>`.

- [ ] **Step 4: Run tests, expect PASS.**

- [ ] **Step 5: Functional smoke run (GPU)**

Run: `phase1-diffusers\.venv\Scripts\python.exe -I phase1-diffusers\generate.py --prompt-id p1-zh-scene --width 1024 --height 1024 --steps 4 --seed 42 --out results\raw\smoke`
Expected: a valid PNG (1024×1024) + sidecar JSON validating against `bench/schema/result.schema.json`. Errors → log issue with full traceback (this is the first full-pipeline ROCm stress; problems here are exactly the ecosystem findings we want recorded).

- [ ] **Step 6: Commit and push** — `feat(phase1): generation CLI with stage timing + smoke image evidence`.

### Task 7: Benchmark harness + baseline run + report

**Files:**
- Create: `bench/run_bench.py`, `bench/make_report.py`, `tests/test_run_bench.py`
- Create (data): `bench/results/2026-10-31/` (result JSONs, `report.md`, plots, contact sheet)

**Interfaces:**
- Consumes: `generate.py` internals via import (`import generate` with sys.path insert, or subprocess — implementer's choice, documented), `bench/prompts.json`, schema.
- Produces: `plan_runs(prompt_ids: list[str], resolutions: list[tuple[int,int]], seeds: list[int], warmup: int=1, measured: int=3) -> list[RunSpec]` where `RunSpec = dict(kind="cold"|"warm"|"measure", prompt_id, width, height, seed, run_idx)`; cold is emitted exactly once for the first spec of the process. `make_report(results_dir: str) -> None` writes `report.md` + `speed_by_config.png` + `step_time_breakdown.png` (matplotlib, `Agg` backend), medians + min/max in every table, run count and protocol version stated, plus a Limitations section (what this benchmark does not measure — e.g. no cross-framework claim yet, single machine, ±run variance).
- Output naming: `<experiment>/<prompt_id>-<seed>-r<idx>.json` under `bench/results/<date>/`.

- [ ] **Step 1: Write failing tests**

`tests/test_run_bench.py`: `test_cold_emitted_once` (over full 3×2×3 matrix: exactly 1 kind=="cold", 6 warmup, 18 measure); `test_matrix_covers_all_combos` (every prompt×resolution×seed appears with `measured` count 3); `test_make_report_smoke` (feed a tmp dir with 2 valid sample JSONs → `report.md` exists and contains the experiment names and "median").

- [ ] **Step 2: Run, expect FAIL.** `uv run --with pytest --with jsonschema --with matplotlib pytest tests/test_run_bench.py -v`

- [ ] **Step 3: Implement `bench/run_bench.py` and `bench/make_report.py`** per Interfaces (pure logic importable without torch; GPU execution path lazy).

- [ ] **Step 4: Run tests, expect PASS.**

- [ ] **Step 5: Execute the baseline (GPU, ~1.5–3h; background)**

Run: `phase1-diffusers\.venv\Scripts\python.exe -I bench\run_bench.py --date 2026-10-31`
Expected: 24 result JSONs (18 measure + 6 warm) + 1 cold record; all validate against schema; images land in gitignored `results/raw/`. VRAM peak captured per run (`torch.cuda.max_memory_allocated`).

- [ ] **Step 6: Generate report + curate evidence**

Run `make_report`; build one contact-sheet grid PNG (PIL) of prompt×resolution sample outputs (~18 tiles at 256px, one image per measure run) into `bench/results/2026-10-31/contact_sheet.png`; copy 6 representative full-res samples (2 per prompt) into the results dir. Verify total image payload < 100MB before commit.

- [ ] **Step 7: Commit and push** — `data(phase1): diffusers baseline v1 — full protocol run, report, evidence`. Update README results table (EN+zh).

### Task 8: Stranger-standard reproduce entrypoint

**Files:**
- Create: `reproduce.ps1`, update `README.md` + `README.zh-CN.md`

**Interfaces:**
- Produces: `reproduce.ps1 -Quick` — checks uv, creates `.venv-repro`, runs the mandated torch command + requirements install, downloads weights if absent (ModelScope), runs ONE config (p2-en-scene, 1024², 40 steps, seed 42), prints wall time and output path, and compares nothing (human reads README table). `-Full` runs Task 7's harness instead.

- [ ] **Step 1: Write `reproduce.ps1`** per Interfaces (idempotent: skips existing venv/weights).

- [ ] **Step 2: Dry-verify structure** — `powershell -NoProfile -Command "Get-Help .\reproduce.ps1 -Parameter Quick"` parses; syntax check via `powershell -NoProfile -Command "[scriptblock]::Create((Get-Content reproduce.ps1 -Raw)) > $null"`.

- [ ] **Step 3: README complete setup section** (EN + zh): prerequisites, reproduce.ps1 usage, manual steps, env table (driver, ROCm build, Python, torch), results summary, limitations link.

- [ ] **Step 4: Commit and push** — `docs: stranger-standard reproduce entrypoint (30-minute bar)`.

---

## Deferred (own plans later)

- Phase 2: ComfyUI baseline (own venv, Comfy-Org weights via ModelScope-or-deviation, API-driven bench).
- Phase 3: optimization experiments (Turbo, fp8, GGUF, attention backends, torch.compile/Triton-on-Windows, VAE tiling, VRAM modes) — each experiment one config change vs baseline, quality gate grids.
- Phase 4: batch RCA + fixes + upstream PRs from `docs/issues/`.

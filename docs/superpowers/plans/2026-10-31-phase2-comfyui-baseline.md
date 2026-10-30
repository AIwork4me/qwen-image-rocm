# qwen-image-rocm Phase 2: ComfyUI Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up ComfyUI on Windows-native ROCm (7900 XTX) in its own uv venv, produce a verified ComfyUI baseline for Qwen-Image-2.1 at 1024² under protocol v1.1, and compare it against the Phase 1 diffusers baseline — all evidence committed to the repo.

**Architecture:** ComfyUI cloned at a pinned commit under `phase2-comfyui/ComfyUI` (gitignored) with its own uv venv using the mandated AMD ROCm torch stack. A benchmark driver talks to ComfyUI's HTTP API (`/prompt`, `/history`, `/view`) programmatically. Shared protocol machinery (plan_runs, steady_step_rate, schema, reporting) is extracted from Phase 1 into `bench/core.py` first, so both frameworks measure identically.

**Tech Stack:** Same ROCm stack as Phase 1 (torch 2.12.0+rocm7.14.1 gfx1100 wheels, mandated command verbatim), ComfyUI (pinned commit), ModelScope-first weights (Comfy-Org split format; HF fallback is the one pre-approved deviation), requests/httpx for the API driver, existing pytest/ruff/matplotlib toolchain.

**Spec:** `docs/specs/2026-10-30-qwen-image-2.1-rocm-7900xtx-design.md` (Phase 2 section + 基准协议 v1 + 公平对比规则 + 开源质量承诺)

## Global Constraints

- Mandated torch install command, verbatim, in the new venv; nothing else may install torch; after every `pip install`, assert `torch.__version__.endswith("rocm7.14.1")`.
- Weights from ModelScope first; Comfy-Org split format via HF is the pre-approved fallback — record the deviation in `docs/weights.md`.
- Protocol v1.1: frozen `bench/prompts.json`, seeds `[42, 1337, 20261030]`, 1024², 40 steps; warm/measure split; medians from `run_kind == "measure"` only; s/step = steady-state (steps 2..N) where step data exists.
- Fair comparison rule: ComfyUI uses its official default sampler/scheduler for Qwen-Image-2.1; the exact sampler/scheduler/steps are recorded in every result JSON (`sampler`, `scheduler` extra fields) and in the report; no cross-framework claim is made beyond quality-level comparison.
- ROCm problems: log to `docs/issues/` (env, full error text, suspected layer); minimal workarounds for hard blockers only, themselves logged. Phase 4 owns RCA.
- Every result JSON validates against `bench/schema/result.schema.json` **before** writing. `attention_backend` recorded.
- Stale-PATH session: absolute paths for git/gh/uv (`"C:\Program Files\Git\cmd\git.exe"`, `"C:\Program Files\GitHub CLI\gh.exe"`, winget uv path). GitHub push is intermittent: commit locally, push opportunistically (chunked pushes with retries work).
- Image evidence ≤100MB per push; `phase2-comfyui/ComfyUI/`, `phase2-comfyui/.venv/`, `weights/` gitignored.
- Commit after every task; upstream-facing artifacts in English.

## Review Focus

- **Silent CPU fallback in ComfyUI**: server starts fine on CPU. Driver must verify `/system_stats` reports the AMD GPU (name contains "7900") before any run; abort otherwise. `check_server` (Task 4) is the gate; first verified at server start (Task 2 Step 3).
- **Attention backend breakage hitting ComfyUI** (the Phase-1 SDPA `hipErrorInvalidValue`): the driver must capture the server log tail into the issue doc on first failure and apply the ComfyUI-side equivalent of the math workaround (launch ComfyUI with `QIR_SDP=math` env honored via a wrapper that sets the torch.backends flags before ComfyUI imports; the server env vars propagate). Pinned in Task 4.
- **pip swapping ROCm torch when ComfyUI requirements install**: ComfyUI `requirements.txt` lists torch — install torch FIRST, then `pip install -r requirements.txt` (satisfied), then the build assert. Pinned in Task 2.
- **Workflow JSON drift** (wrong model filenames / node class names silently queueing forever): driver validates workflow node classes exist by posting to `/object_info` before the run; poll timeout with clear error. Pinned in Task 4.
- **Timer catching queue wait**: ComfyUI runs queue sequentially — time from queue-submission to completion includes wait. Driver must run configs sequentially (single-item queue) and record `execution_time` from history separately from wall time. Pinned in Task 5.

---

### Task 1: Extract shared bench core (refactor, TDD-guarded)

**Files:**
- Create: `bench/core.py`
- Modify: `bench/run_bench.py`, `bench/make_report.py` (import from core; delete moved code)
- Test: existing `tests/test_run_bench.py` (moves with the code); Create `tests/test_core.py`

**Interfaces:**
- Produces: `bench/core.py` with `plan_runs(prompt_ids, resolutions, seeds, warmup=1, measured=3) -> list[dict]`, `steady_step_rate(step_times) -> float | None`, `load_schema() -> dict`, `validate_record(record) -> None` (raises on invalid), `PROMPTS_PATH`, `REPO`.
- Existing `bench.run_bench.plan_runs` / `bench.make_report.steady_step_rate` keep importable (re-export from core) so old entry points don't break.

- [ ] **Step 1: Write failing test** — `tests/test_core.py`: `test_core_exports` imports all five names from `bench.core` and asserts `plan_runs(["a"], [(1024,1024)], [42])` yields 1 cold + 1 warmup + 1 measure; `test_validate_record_rejects_bad` passes a dict missing `seed` to `validate_record`, expects `ValidationError`.
- [ ] **Step 2: Run** `uv run --with pytest --with jsonschema --with matplotlib pytest tests/ -v` — **FAIL** (`No module named bench.core`).
- [ ] **Step 3: Implement** `bench/core.py` by moving the three functions + constants from run_bench/make_report (verbatim bodies), re-export in the old modules, point local uses at core.
- [ ] **Step 4: Run full suite** — **PASS** (16 tests).
- [ ] **Step 5: Commit** `refactor(bench): extract shared core (plan_runs, steady_step_rate, schema) for cross-framework reuse`.

### Task 2: ComfyUI clone + venv + mandated torch + server GPU verification

**Files:**
- Create: `phase2-comfyui/` (gitignored ComfyUI clone + venv), `phase2-comfyui/setup.md` (pinned commit + install log summary), `phase2-comfyui/launch_comfyui.ps1`

**Interfaces:**
- Produces: `phase2-comfyui/.venv` with the ROCm stack; ComfyUI clone at `phase2-comfyui/ComfyUI` at recorded commit SHA; `launch_comfyui.ps1 -Port 8188` that starts the server with `QIR_SDP=math` env honored, `--listen 127.0.0.1`, and returns only when `/system_stats` responds.

- [ ] **Step 1: Clone + record commit**

`git clone https://github.com/comfyanonymous/ComfyUI phase2-comfyui/ComfyUI` (github clone may need retries like pushes — retry loop ≤5); record `git -C phase2-comfyui/ComfyUI rev-parse HEAD` in `phase2-comfyui/setup.md`.

- [ ] **Step 2: venv + mandated torch (verbatim) + ComfyUI requirements**

`uv venv phase2-comfyui/.venv --python 3.12 --seed`; run the mandated torch command verbatim with that venv's python; then `python -m pip install -r phase2-comfyui/ComfyUI/requirements.txt`; then the build assert (`torch.__version__.endswith('rocm7.14.1')`). If requirements tried to touch torch and the assert fails: reinstall via mandated command, log issue.

- [ ] **Step 3: Write launch script + first server start**

`launch_comfyui.ps1`: sets `QIR_SDP=math` then starts `python main.py --listen 127.0.0.1 --port 8188 --extra-model-paths-config ../extra_model_paths.yaml` (config file created in Task 3; script tolerates absence for the GPU check). No `$ErrorActionPreference='Stop'` (Phase-1 lesson: PS5.1 kills native stderr).
Start server (background); poll `GET /system_stats` (≤120s).
Expected: JSON with `devices[].name` containing `7900` (comfy backend `pytorch`, type `hip` or similar). If attention errors appear in server log at import: log issue + adjust.

- [ ] **Step 4: Commit** `feat(phase2): ComfyUI env (pinned <sha>) with ROCm stack, GPU-verified server` — commit only setup.md + launch script.

### Task 3: Weights for ComfyUI (ModelScope first, HF fallback)

**Files:**
- Create: `phase2-comfyui/extra_model_paths.yaml`, `docs/weights.md` (append ComfyUI section)

**Interfaces:**
- Produces: `weights/comfyui-split/` laid out as `diffusion_models/`, `text_encoders/`, `vae/` (Comfy-Org split format), mapped via `extra_model_paths.yaml` so ComfyUI sees them under those categories.

- [ ] **Step 1: ModelScope availability check** — `modelscope` CLI/`gh`-equivalent search for a Comfy-Org split mirror of Qwen-Image-2.1 (`modelscope download --model Comfy-Org/Qwen-Image-2.1` dry attempt; also check `AI-ModelScope` style mirrors programmatically via modelscope hub API if CLI is unclear).
- [ ] **Step 2: Download** — ModelScope path if found; else HF (`huggingface-cli`/`hf download Comfy-Org/Qwen-Image-2.1 --local-dir weights/comfyui-split`) — the pre-approved deviation, recorded in `docs/weights.md` with exact commands + file list + sizes (~25GB). HF endpoint blocked → try `HF_ENDPOINT=https://hf-mirror.com` (record if used).
- [ ] **Step 3: Map + verify** — write `extra_model_paths.yaml` mapping the three dirs; restart server (Task 2 script); verify via `GET /object_info` that the new model names appear in `UNETLoader`/`CLIPLoader`/`VAELoader` enums.
- [ ] **Step 4: Commit** `docs(phase2): comfyui split weights procedure + model path mapping`.

### Task 4: Smoke workflow via API (one image)

**Files:**
- Create: `phase2-comfyui/workflow_qwen21_t2i.json` (API format), `bench/comfyui_client.py`

**Interfaces:**
- Produces: `bench/comfyui_client.py` with `build_workflow(*, unet: str, clip: str, vae: str, prompt: str, negative: str, width: int, height: int, steps: int, seed: int, sampler: str, scheduler: str) -> dict` (pure), `post_prompt(base_url: str, workflow: dict) -> str` (prompt_id), `wait_for_result(base_url: str, prompt_id: str, timeout_s: int = 1800) -> dict` (history entry; raises with server-log pointer on timeout), `fetch_image(base_url: str, history: dict) -> bytes`, `check_server(base_url: str) -> None` (raises unless a device name matches "7900").

- [ ] **Step 1: Write failing tests** — `tests/test_comfyui_client.py`: `test_build_workflow_nodes` (expected node classes: UNETLoader/CLIPLoader/VAELoader/CLIPTextEncode×2/EmptyLatentImage/KSampler/VAEDecode/SaveImage; seeds/size/steps wired); `test_build_workflow_seed_mapping` (KSampler.seed == given seed, no inputs wired as widgets).
- [ ] **Step 2: Run** — **FAIL** (module missing).
- [ ] **Step 3: Implement client** (pure parts testable; HTTP via `requests` lazily imported inside functions so tests stay torch/GPU-free).
- [ ] **Step 4: Run** — **PASS**; full suite green.
- [ ] **Step 5: Live smoke** — server up; `check_server`; build workflow for `p1-zh-scene` 1024² 4 steps seed 42 (sampler/scheduler: ComfyUI official Qwen-Image-2.1 defaults — pin exact values discovered from the official example workflow bundled in the Comfy-Org repo / ComfyUI templates; record in setup.md); save PNG to `results/raw/smoke-comfyui/`.
Expected: valid 1024×1024 PNG. Any attention error → capture server log tail → issue doc → apply/verify workaround env and retry once.
- [ ] **Step 6: Commit** `feat(phase2): ComfyUI API client + smoke image (first ComfyUI-generation on this stack)`.

### Task 5: ComfyUI benchmark driver

**Files:**
- Create: `bench/run_comfyui.py`
- Test: `tests/test_run_comfyui.py`

**Interfaces:**
- Consumes: `bench.core.plan_runs`, `bench.comfyui_client.*`, schema validation, `steady_step_rate`.
- Produces: `main() -> None` (argparse: `--date`, `--resolutions 1024`, `--base-url http://127.0.0.1:8188`, `--out-dir bench/results/<date>`); per spec one JSON per run (`run_kind`, `attention_backend: "comfyui-default"`, extra fields `sampler`, `scheduler`, `execution_time_s` from history, `step_times_s: []`, `denoise_s: execution_time_s` — approximation documented in report limitations); wall `total_s` measured around submit→completion with sequential single-item queue; images to `results/raw/<date>/`.

- [ ] **Step 1: Failing tests** — `test_result_record_fields` (built record validates against schema and carries sampler/scheduler/execution_time_s), `test_sequential_queue` (driver never has >1 pending prompt: asserted by inspecting the plan order = `plan_runs` output order).
- [ ] **Step 2: Run** — **FAIL**.
- [ ] **Step 3: Implement** driver (server assumed external; driver refuses to start if `check_server` fails).
- [ ] **Step 4: Run** — **PASS**.
- [ ] **Step 5: Commit** `feat(bench): ComfyUI protocol driver (API-driven, sequential queue)`.

### Task 6: Full protocol run (GPU)

- [ ] Start server via launch script; run `run_comfyui.py --date <today>-comfyui-1024` (cold + 3 configs × (warmup + 3 measures)); monitor.
Expected: 13 result JSONs, all schema-valid, images on disk. ROCm problems → issue docs.

### Task 7: Report + cross-framework comparison + README

**Files:**
- Create: `bench/results/<date>-comfyui-1024/report.md` (+ plots), `bench/results/<date>-comfyui-1024/cross_framework.png` (side-by-side grid: ComfyUI vs diffusers, same prompt/seed), README.md + README.zh-CN.md results tables.

- [ ] **Step 1:** run `make_report` on the ComfyUI dir; append ComfyUI limitation notes (denoise_s = execution_time approximation; sampler/scheduler defaults recorded).
- [ ] **Step 2:** build cross-framework grid (reuse `make_contact_sheet` tile logic; 6 tiles: 3 prompts × 2 frameworks, seed 42 measure run); copy 2 curated samples; verify ≤100MB.
- [ ] **Step 3:** README EN+zh: Phase 2 table (median total, execution time, VRAM; sampler/scheduler used) + framework-gap note (ComfyUI vs diffusers total at same config).
- [ ] **Step 4:** Commit `data(phase2): ComfyUI baseline 1024-sq — protocol v1.1, report, cross-framework evidence`.

### Task 8: Final review + push

- [ ] Fresh subagent whole-branch review (review-package; Review Focus above verbatim; ledger rulings).
- [ ] Fix Critical/Important with tests; ledger minors.
- [ ] Push (chunked-with-retry if needed) until `origin/main == HEAD`; confirm CI green via `gh api` (actions runs).

## Deferred (later plans)

- Phase 3 optimization experiments (Turbo, fp8, GGUF, backends, tiling).
- Phase 4 batch RCA + upstream PRs.
- ComfyUI custom-node benching (GGUF etc.) — Phase 3.

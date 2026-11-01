# Final release audit (independent pass) — 2026-11-01

Auditor role separated from author role; nothing below passes "because I
wrote it" — each verdict cites its check. Gate vocabulary: PASS / FAIL /
BLOCKED / NOT APPLICABLE (no "basically done").

## The 15-point checklist

| # | Question | Verdict | Check performed |
|---|---|---|---|
| 1 | README accurate? | **PASS** | every number cross-checked against `docs/benchmarks/CLAIM_EVIDENCE_MATRIX.md` rows and their record files; 5.2–5.5× carries same-session-paired qualifier; 2048² carries probe-tier qualifier |
| 2 | First screen compelling in 30 s? | **PASS** | hero table (what/how fast/what GPU/what stack) + 6 real images within two viewports; problem statement up top |
| 3 | Real images only? | **PASS** | gallery = unedited run outputs, `docs/gallery/PROVENANCE.md` maps each to experiment/prompt/seed/steps; social preview built by `tools/make_gallery_assets.py` from the same files (CJK rendering visually verified) |
| 4 | Install commands work on a clean env? | **PASS** (bounded) | three layers: (a) fresh GitHub runner = clean clone, CI green in 14 s; (b) clean local clone in a *differently-named* dir (`qir-acceptance`) — full quickstart provisioning (venv + AMD wheels + pinned ComfyUI clone + generation) executed, see §Independent clone; (c) not exercised: fresh-machine weight download end-to-end (18 GB) — downloader resume/sha256 logic is unit-covered and was exercised in phase 3, but a from-zero 18 GB download was not re-timed this session |
| 5 | Unverified speed claims? | **PASS** | the previously-unmeasured "recommended triple" was measured this session (r1, n=9) before any README exposure; levers' ratios never multiplied |
| 6 | Cached speed sold as user experience? | **PASS** | REAL_WORLD_LATENCY.md separates cold (12–17 s) / fresh (~10 s) / warm (8–9 s); README headline carries "warm" inline |
| 7 | Single 2K probe oversold? | **PASS** | 2048_VALIDATION.md ledger (2 probes, tier stated); README says "demonstrated + re-probed"; multi-seed matrix = issue #4 |
| 8 | Unconditional quality-lossless claims? | **PASS** | turbo/ck = "different images, human-judged"; int8 = "near-lossless (LPIPS band)"; only nosmart/Quality = "bit-identical"; forbidden-framings list enforced in matrix |
| 9 | Model/framework pinned? | **PASS** | torch version-suffix assert in both quickstart and reproduce; ComfyUI pinned commit + drift warning; manifest-driven generation (no flag soup) |
| 10 | Wrong GPU-support claims? | **PASS** | support matrix: tested = 7900 XTX only; quickstart fail-closes on non-Radeon, requires `-AllowUntestedGpu` for other Radeons |
| 11 | CI green? | **PASS** (branch) | PR #7 CPU test gate green (run 41281913975). Note: `main` stays red until this PR merges — that is the expected pre-merge state |
| 12 | Important results traceable? | **PASS** | claim→evidence matrix + per-run JSON records + env snapshots + provenance file |
| 13 | Historical benchmarks polluted? | **PASS** | `git diff main..HEAD --stat -- bench/results/2026-1{0,1}* ` shows only NEW directories + today's new dirs; no historical file touched |
| 14 | License / sensitive-info problems? | **PASS** | secret-pattern scan clean on all newly committed logs (command in LEGAL doc); maintainer's local paths inside committed logs documented as accepted evidence residue; no weights committed (`.gitignore` + tree check); LEGAL_AND_ATTRIBUTION covers model licenses & non-affiliation |
| 15 | Dangerous process-kill / file deletion? | **PASS** | `run_variant.ps1` + quickstart rewritten: kill only own orphans (command-line-matched to this repo), spare-port fallback, no recursive deletes outside the venv it created; audit diff-read both scripts |

## Independent clone acceptance

Fresh clone of the PR branch into `%TEMP%\qir-acceptance\repo` (different
directory name than any dev checkout — also proves checkout-path
independence beyond CI's `qwen-image-rocm` name):

| Step | Result |
|---|---|
| Clone + CPU tests in clean dir | PASS — 66/66 green via `uv run … pytest` in the clone (dir name `repo` — third distinct checkout name after `image` and `qwen-image-rocm`) |
| `.\quickstart.ps1 -Mode Fast` full provisioning | PASS, exit 0 — fresh venv, pinned AMD wheels installed (torch suffix asserted: 2.12.0+rocm7.14.1), ComfyUI cloned at pinned commit from github, weights state = present (content-verified files shared via junction; the from-zero download path is unit-covered + phase-3-exercised, not re-downloaded), server health-gated on the 7900, cold+warm generation via the benchmark driver, teardown clean |
| Timings from the clone (provisioning-fresh, no warm page cache) | boot 28.3 s · cold 17.2 s (TE 5.03 s — cold-cache text encode) · warm 8.57 s avg · total wall 73.9 s for 4 images — regime consistent with the dev-tree dogfood; the slower boot/cold are the honest "first launch on a new install" numbers |
| Quality mode from clean clone | NOT RUN (bounded scope; same code path, heavier model set — historical + dev-tree evidence stands) |
| 2048 from clean clone | NOT RUN (probe evidence stands from r2) |

Weights note: the acceptance clone shares the already-downloaded,
LFS-verified weight files (junction). The from-zero 18 GB download path
(resume + sha256) is unit-tested and was production-tested during phase 3,
but was not re-downloaded from scratch in this acceptance to bound network
cost — recorded as NOT TESTED (this session).

## Verdict

**READY FOR OWNER REVIEW.** Blockers before a v0.1.0 stable tag (tracked):
#5 owner verdict on the triple grid (required), #4 2048 bounded matrix
(recommended). Social preview upload is a manual owner step (asset ready).
No auto-merge performed; no tag created.

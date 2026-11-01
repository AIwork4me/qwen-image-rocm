# Final release audit (independent pass) — 2026-11-01

## Current Final Release Assessment (closure round 3 — supersedes everything below)

- **Engineering gates: PASS.** CPU CI green on the PR HEAD (check the PR's
  latest run); 101/101 tests, ruff clean; every public median recomputed
  from committed records by `tests/test_evidence_numbers.py`.
- **Fidelity semantics:** the last hardcoded assumption ("closer to the
  bf16 reference") is gone from the generator and from the r1 report —
  LPIPS fidelity now reads "closer perceptual similarity to the specified
  baseline image; not an absolute image-quality score", pinned by
  `tests/test_quality_gate_semantics.py` (cases 1–6).
- **Evidence tiers (current):** 1024² Fast triple = MEASURED (n=9 + fresh
  arms); 2048² Fast = **MEASURED — BOUNDED MATRIX** (3 prompts × 3 seeds,
  `2026-11-01-r3-2048matrix/`, issue #4 CLOSED). Soak / OOM-recovery /
  multi-hour stability: **NOT claimed**.
- **Owner-decision state:** issue #5 (formal quality verdict on the triple
  grid) is **OPEN by design** — owner materials at
  [OWNER_QUALITY_REVIEW.md](OWNER_QUALITY_REVIEW.md). AI observations there
  are non-binding and clearly labeled.
- **Release state:** PR #7 not merged; no tag; no GitHub release.
- **Verdict: MERGE GATE READY · STABLE RELEASE GATE BLOCKED (owner quality
  verdict pending).**

The sections below this line are retained as audit history:

> **Revision round 2** (same day, owner-requested independent review):
> every finding from the review was fixed and re-verified; a round-2
> section follows the original 15-point checklist. The live port-safety
> test in round 2 caught an additional REAL defect the original audit
> missed (PS 5.1 cold-CIM flakiness) — evidence that behavioral testing
> beats source review.

Auditor role separated from author role; nothing below passes "because I
wrote it" — each verdict cites its check. Gate vocabulary: PASS / FAIL /
BLOCKED / NOT APPLICABLE (no "basically done").

## The 15-point checklist — Historical Round-1 Snapshot (Superseded)

*State as of round 1 (pre-revision). Issue #4 was then open, 2048² was
probe-tier, CI references point at the round-1 run. Kept verbatim for audit
trail; see the Current Final Release Assessment above and the round-2 table
below for what changed.*

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

## Independent clone acceptance — Historical Round-1 Snapshot (Superseded by round-2 re-runs)

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

## Verdict — Historical Round-1 Snapshot (Superseded; #4 has since been executed and closed)

**READY FOR OWNER REVIEW.** Blockers before a v0.1.0 stable tag (tracked):
#5 owner verdict on the triple grid (required), #4 2048 bounded matrix
(recommended). Social preview upload is a manual owner step (asset ready).
No auto-merge performed; no tag created.

---

# Revision round 2 — independent-review findings, fixed & re-verified

| # | Review finding | Fix | Verification |
|---|---|---|---|
| P0-1 | r1-triple quality.md labeled its baseline "bf16, 40 steps" (hardcoded) while the actual baseline was E8 turbo-int8/bf16-TE/ck @8 steps | `describe_baseline()` derives the label from the baseline's own run records; `--baseline-desc` override; fail-safe text when no records; quality.json machine echo added | quality.md regenerated (LPIPS values identical — deterministic rerun); `tests/test_quality_gate_baseline_desc.py` (6 tests incl. committed-md assertions) |
| P0-2 | LPIPS per-prompt mapping transposed in docs (0.012/0.058/0.014 presented as p1/p2/p3) | corrected everywhere to p1=0.058 / p2=0.012 / p3=0.014 (original values untouched) | grep-verified across README/zh/CHANGELOG/matrix/methodology/delivery + PR #7 body + issue #5 body edited; mapping now PINNED by a test reading quality.json |
| P0-3 | kill-by-command-line-string ownership; default killed existing listeners | `bench/portops.ps1`: PID-tree ownership only; existing listeners never touched (spare-port fallback); teardown = own started tree only; `-KeepServer` honored with printed PIDs; string matching deleted | static contract tests (7) + **live dual-checkout test**: decoy with "phase2-comfyui" in its command line held 8188 through a full Fast run (untouched), quickstart took 8189, teardown freed 8189, decoy survived until manually killed |
| P0-3b (found live) | **PS 5.1 cold-CIM flake**: the first NetTCPIP/CIM query in a fresh process transiently returns empty → occupied port read "free" → server died on bind | `Test-PortBusy` now **bind-probes** (the same syscall the server uses); CIM warmed at dot-source for informational queries | reproduced (porttest -File said False while bind failed), fixed, re-run of the full live test passed; minimal repro + fix rationale in code comments |
| P0-4 | size-only "present" check = digest bypass for pre-existing files | revision `aacf31a6` pinned; sha256 table embedded in-repo (provenance: LFS pointers via mirror AND full local-file hashes — 8/8 match); digest enforced for EVERY file EVERY run; stamp cache keyed size+mtime (corruption re-hashes); official-vs-mirror distinction documented (trust anchor = in-repo table, not transport) | live run verified all three Fast files + all three Quality files; injection tests: same-size-wrong-content FAILS, truncated FAILS, absent FAILS, cache cannot mask corruption |
| P0-5 | ComfyUI commit drift only warned; `-SkipSetup` skipped verification | drift fails closed unless `-AllowComfyCommitDrift` (run recorded `stack_verified=false` in provisioning.json); `-SkipSetup` still verifies torch pin + commit + digests | static contract tests; live runs printed pinned-commit OK and `stack_verified=True` |
| P0-6 | "cold start" conflated ready-to-first with full cold | unified 4-metric vocabulary (Server boot / Ready-to-first-image / Full cold start / Warm mean+median) in quickstart output, provisioning.json, REAL_WORLD_LATENCY, READMEs, rc1 | live output shows all four; docs audited for stale wording |
| P0-7 | triple verdict must stay PENDING until #5 | READMEs (en/zh) now state verdict status explicitly: turbo-int8+ck judged (A1); triple = LPIPS-gated, formal verdict PENDING #5 | wording sweep + zh/en consistency audit script (all key numbers/labels present in both, no stale forms) |
| P1-8 | GPU workflow assumed venv/weights exist | runs full quickstart (no -SkipSetup) on a clean checkout; snapshot moved after provisioning; drift fails closed there | workflow file rewritten; same provisioning path live-verified earlier in the clean-clone acceptance |
| P1-9 | step_times_s completeness unchecked | `tools/check_step_times.py` + tests; corpus scanned: 337 records → 183 complete / **105 incomplete** (step-1 event loss in warmup/fresh/cold) / 49 monitor-absent (pre-v1.3) | finding documented in REAL_WORLD_LATENCY + no published number derives from step arrays (totals/node timings are server-side) — verified by re-reading claim sources |
| P1-10 | quickstart dirtied the git worktree; run_variant could clobber records | results under gitignored `bench/results/quickstart/`; `run_variant` refuses existing record dirs without `-OverwriteResults` | live run left `git status` clean; overwrite guard present + contract-tested |
| #4 | 2048² bounded matrix not executed | executed: `2026-11-01-r3-2048matrix/` | medians 40.27/40.32/40.36 s (p1/p2/p3 — **first 2048² typography runs**), all measures 40.24–40.45 s, cold 47.5 s, sampled VRAM 8.3–12.6 GB; issue #4 closed with data; docs/matrix/rc1/READMEs upgraded from probe-tier wording |

## Round-2 gate summary

- CPU tests: **91 passed** (66 → 91: quickstart suite 11→15 with digest
  injection/cache tests; +7 baseline-desc; +5 step-times audit; +9 PS
  safety contracts), ruff clean
- Live GPU regressions after the changes: Fast exit 0 (full cold start
  20.3 s, warm mean 8.15 s), Quality exit 0 (full cold start 63.1 s, warm
  mean 46.22 s), 2048 matrix exit 0 (13 records)
- Historical evidence untouched (`bench/results` additions only; no edits
  to pre-existing record files — r1 quality.md regenerated by the fixed
  tool with identical numbers, label corrected as an errata of our own
  round-1 file, not of frozen phase-3 evidence)
- Remaining blocker before a stable tag: **#5 owner verdict only**
  (+ manual social-preview upload). Status: **READY FOR FINAL OWNER
  REVIEW**.

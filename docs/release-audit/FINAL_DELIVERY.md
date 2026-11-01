# Final delivery report — release-ready v0.1.0-rc1 (2026-11-01)

> **Current state (closure round 3):** sections A–H below are a
> **Historical Round-1 Snapshot — Superseded** (issue #4 open at the time,
> round-1 HEAD/CI references; kept verbatim, failures included). The
> revision-round-2 addendum at the bottom fixed all review findings, and
> the closure round fixed the last fidelity-semantics hardcode with
> regression pinning. Current gates:
> **MERGE READY · STABLE RELEASE BLOCKED (owner quality verdict #5
> pending)** — see [FINAL_AUDIT.md](FINAL_AUDIT.md) §Current Final Release
> Assessment and [OWNER_QUALITY_REVIEW.md](OWNER_QUALITY_REVIEW.md).

## A. What was actually done — Historical Round-1 Snapshot

**P0 (all closed)**

1. **CI fixed & gates split** — root cause of red main was a
   checkout-directory-name assertion; replaced with structural root
   assertions; CI renamed to an explicit **CPU test gate** + new manual
   **self-hosted GPU hardware validation** workflow (hosted runners make no
   GPU claims).
2. **Benchmark claims audited → matrix** — the previously *unmeasured*
   "recommended production triple" was measured as a whole on the target
   GPU (n=9 + fresh-prompt arms) before being exposed in any public text;
   `CLAIM_EVIDENCE_MATRIX.md` binds every public claim to records, with a
   forbidden-framings list.
3. **Real-user performance defined** — cold / fresh-prompt / warm measured
   separately (quickstart dogfood + r1 fresh arms); VRAM semantics labeled
   (sampled 0.5 s = lower bound; N/A allowed, never 0).
4. **Fast Path shipped** — `quickstart.ps1` Fast/Quality: full check chain,
   pinned stack, sha256-verified resumable downloads, port-safe lifecycle,
   no silent CPU fallback; dogfooded end-to-end on the 7900 XTX in both
   modes; `run_variant.ps1` no longer kills strangers' processes.
5. **2048² evidence hardened** — second-session re-probe (40.2 s warm) +
   tier ledger doc; multi-seed matrix tracked as issue #4.
6. **Quality semantics corrected** — LPIPS fidelity/distance semantics,
   verdict ledger, "no PASS without a completed evaluation"; triple's
   formal verdict honestly PENDING (issue #5).

**P1** — product README (EN/中文 mirrors, real gallery + provenance,
support matrix, social preview CJK-verified); GitHub description + 10
topics set; issue templates ×3 + PR template; CONTRIBUTING /
TROUBLESHOOTING / CHANGELOG; LEGAL_AND_ATTRIBUTION (license boundaries,
no-weights rule, log-scan policy, non-affiliation); v0.1.0-rc1 staged
(owner-gated); 66 CPU tests + ruff green.

**P2** — LAUNCH_KIT with qualifier-carrying drafts (release, LinkedIn, X,
Reddit, 中文社区, maintainer outreach) — nothing auto-posted.

## B. Problems → root cause → fix → test evidence

| Problem | Root cause | Fix | Evidence |
|---|---|---|---|
| CI red on every main push | `test_core_exports` asserted `REPO.name == "image"` (local dir name); GitHub checks out `qwen-image-rocm` | structural assertions (`REPO` contains `bench/core.py`; PROMPTS/SCHEMA files exist) | local 55/55 → PR #7 fresh runner green (run 41281913975, 14 s) |
| Recommended config claimed but never measured as a whole | phase-3 manifests measured pairs only (e8 used bf16 TE, no nosmart) | measured the triple (new manifest + run) | r1-triple records: 8.30/9.06/8.09 s (n=9), fresh 10.0 s, cold 17.1 s; LPIPS vs e8 0.058/0.012/0.014 |
| 9.1 s sold without regime; cold/fresh/warm conflated | warm-only benchmark framing | quickstart prints all three; REAL_WORLD_LATENCY.md | quickstart-Fast-20261101-142448 + r1 fresh arms (TE 1.22–1.24 s, cache-busted) |
| `run_variant.ps1` killed any listener on 8188 | unconditional `Kill-Port` pre-start | own-orphans-only (command-line matched) + spare-port fallback | code + parse check; exercised in 4 server lifecycles today without touching foreign processes |
| quickstart first dogfood failed (config) | missing `jsonschema` in the uv env used for `config` | added to the invocation | second dogfood run PASS |
| PS 5.1 multi-line JSON pipeline parse | array-of-lines piped to ConvertFrom-Json | join-then-parse everywhere | third dogfood run PASS (weights GB display correct) |
| 2048² capability based on one probe | single-prompt n=1 evidence | re-probed on the triple config, different session+prompt; ledger written | r2-2048fast: warm 40.2 s / cold 43.3 s / sampled peak 8.3 GB |
| Ruff E501/E702 in new tool | long captions; semicolons | wrapped; amended | `ruff check .` clean |
| Test referenced an untracked manifest (CI red on first PR run) | manifest never `git add`-ed (local passes, runner fails — the audit's warned drift class) | committed; noted as process lesson | PR re-run green in 14 s |

## C. Real Radeon GPU verification summary

- **GPU/OS/driver**: RX 7900 XTX (gfx1100) · Windows 11 build 26300 ·
  Adrenalin 32.0.21030.2001 · torch 2.12.0+rocm7.14.1 (HIP 7.14.60850) ·
  ComfyUI `b5a43215` · snapshot `snapshot-20261101-141420.json`
- **Fast @1024² (8 steps)**: cold 12.1–17.1 s · fresh prompt 10.0 s ·
  warm 8.0–9.2 s (medians 8.30/9.06/8.09; n=9) · sampled VRAM ≈ 7.7 GB
- **Quality @1024² (40 steps)**: cold 59.4 s (TE 7.46) · warm 45.6–46.3 s
  (historical band 45–51 ✓)
- **Fast @2048²**: cold 43.3 s · warm 40.2 s (probe tier)
- **Server boot** (launch→healthy): 8.1 s (warm cache; reboot-cold NOT
  TESTED)
- **Quality gates**: triple vs e8 LPIPS 0.058/0.012/0.014 (max 0.075);
  Quality bit-identical per phase-3 SHA256 gate
- **Samples**: `bench/results/{2026-11-01-r1-triple, 2026-11-01-r2-2048fast,
  quickstart-Fast-20261101-142448, quickstart-Quality-20261101-142606}/`
- **Independent clean-clone acceptance**: see FINAL_AUDIT.md §Independent
  clone — full provisioning (fresh venv + AMD wheels + pinned ComfyUI clone)
  + Fast generation in a differently-named directory, exit 0: boot 28.3 s ·
  cold 17.2 s · warm 8.57 s · 4 images in 73.9 s wall (Quality/2048 not
  re-run there — bounded scope)

## D. README transformation

- Hero: title/subtitle + 5-row verified-numbers table with meaning columns
- 6 real images (gallery + phase-2 baseline + paired grid) with PROVENANCE
- Quick Start 3 commands incl. 2048; Fast-vs-Quality table; support matrix;
  latency table; reproduce commands; results table with quality column;
  findings → 7 upstream links; roadmap; contributing; licenses
- 中文镜像同步（README.zh-CN.md）
- Social preview `assets/social-preview.png` (1280×640, CJK-verified) —
  **upload is a manual owner step** (Settings → Social preview)

## E. CI

- Branch PR #7 CPU test gate: **PASS** —
  https://github.com/AIwork4me/qwen-image-rocm/actions/runs/41281913975
- `main` remains red until PR merge (pre-merge state; fix rides this PR)

## F. GitHub deliverables

- Branch: https://github.com/AIwork4me/qwen-image-rocm/tree/release/trending-ready-v0.1.0
- PR: https://github.com/AIwork4me/qwen-image-rocm/pull/7
- HEAD: `dfe8c79` (tree `28f3282`) at delivery time
- CI: run 41281913975 (green)
- Final audit: `docs/release-audit/FINAL_AUDIT.md`
- Release candidate: `docs/releases/v0.1.0-rc1.md`
- Issues #1–#6 (findings tracking ×3, 2048 matrix, owner verdict,
  GPU-compat call), labels, description + topics set

## G. Remaining items

| Item | Class |
|---|---|
| Owner verdict on triple grid (#5) | BLOCKER (tag gate) |
| 2048² bounded matrix (#4) | RISK-bounded (~15 min GPU) |
| Social preview manual upload | DEFERRED (owner, 1 min) |
| Rebooted-cold-boot measurement | DEFERRED (roadmap) |
| From-zero 18 GB weight download re-timing | DEFERRED (logic unit+phase-3 covered) |
| main red until merge | resolves with PR #7 |

## H. Merge recommendation

**READY FOR OWNER REVIEW** (not self-merged by design).

---

# Revision round 2 — delivery addendum (2026-11-01, same day)

Owner-requested independent review produced 7 P0 + 4 P1 findings. All
fixed; verification summary (full detail in FINAL_AUDIT round-2 table):

- **P0-1/2 evidence integrity**: quality.md baseline label now derived from
  records (the r1 file claimed "bf16, 40 steps" vs actual E8 baseline);
  LPIPS p1/p2/p3 mapping corrected repo-wide + in PR #7 body and issue #5
  (p1=0.058 / p2=0.012 / p3=0.014; pinned by tests via quality.json).
- **P0-3 process safety**: PID-tree ownership (`bench/portops.ps1`),
  listeners never killed, `-KeepServer` honored; live dual-checkout decoy
  test passed — and caught a **real PS 5.1 defect** (first CIM query in a
  fresh process reads empty → port check now bind-probes).
- **P0-4 weight integrity**: pinned revision `aacf31a6` + embedded sha256
  table (LFS-pointer ↔ local-hash cross-check 8/8); digests enforced for
  pre-existing files too; same-size-wrong-content injection tests fail
  correctly; stamp cache cannot mask corruption.
- **P0-5 stack verification**: ComfyUI commit drift fails closed
  (`-AllowComfyCommitDrift` = experimental, `stack_verified=false`
  recorded); `-SkipSetup` still verifies torch/commit/digests.
- **P0-6/7 wording**: unified cold-start vocabulary (Server boot /
  Ready-to-first-image / Full cold start / Warm mean+median) everywhere;
  triple verdict remains PENDING (#5) in both READMEs.
- **P1-8/9/10**: GPU workflow provisions clean checkouts; step-times audit
  (105/337 records partial — inventoried, no published number derives from
  them); quickstart results gitignored; run_variant overwrite guard.
- **Issue #4 EXECUTED**: `2026-11-01-r3-2048matrix/` — 3 prompts × 3 seeds
  at 2048², medians 40.27/40.32/40.36 s (incl. first-ever typography
  runs), spread 0.5%, cold 47.5 s, sampled VRAM 8.3–12.6 GB; issue closed
  with data; claim C3 upgraded PROBED → MEASURED (bounded matrix).
- **Re-verification**: 91/91 CPU tests, ruff clean, live Fast + Quality
  regressions exit 0 (full cold 20.3 s / 63.1 s), zh/en consistency audit
  clean, worktree stays clean after user runs.

Remaining before a stable tag: **#5 owner verdict** (+ manual
social-preview upload). Not merged, not tagged, not released.


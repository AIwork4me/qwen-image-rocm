# Troubleshooting

Ordered by how often each one bites. All tested on RX 7900 XTX / Win 11 /
torch 2.12.0+rocm7.14.1.

**`uv: command not found` / quickstart says "uv not found"**
Install it: `winget install --id=astral-sh.uv -e` (quickstart also checks
the default winget path automatically).

**AMD wheel install fails / times out** (`repo.amd.com`)
Re-run — pip resumes. From mainland-China networks see
[docs/weights.md](weights.md) for the measured mirror notes. Never swap the
`--index-url`: a PyPI torch silently replaces the ROCm build (quickstart
asserts the version suffix after every install and fails closed).

**`torch.cuda.is_available()` false / gfx1100 check fails**
Adrenalin driver missing or too old → install/repair, reboot. The quickstart
never falls back to CPU on purpose.

**Weight download stalls (hf-mirror)**
`tools/download_parallel.py` resumes byte-exact per chunk — kill it and
re-run `.\quickstart.ps1` anytime. Set `$env:HF_ENDPOINT` to switch mirror.
Verify step compares against the host's LFS sha256; a mismatch triggers one
automatic re-download, then fails with instructions.

**Port 8188 busy**
quickstart/run_variant never kill a process they didn't start: they fall
forward to a spare port automatically. To use a specific port: `-Port <n>`.

**2048² Quality mode refused**
By design: bf16 VAE decode allocates ~20.25 GB and OOMs on 24 GB
(evidence: docs/issues/evidence/sdpa-7140-2048-vae-oom.log). Use
`-Mode Fast -Resolution 2048`.

**First generation after boot is slow (pagefile thrash)**
Known finding 4 on 32 GB-RAM hosts with the bf16 stack; recovers after
warmup. Fast mode's int8 weights mostly avoid it.

**`TritonMissing` / torch.compile errors**
Expected on Windows ROCm — no Triton wheels published (finding 3). Not a
bug in your setup.

**flash/mem-efficient SDPA `hipErrorInvalidValue` in your own code**
Finding 1 — use the math workaround (`QIR_SDP=math`) like our launchers, or
torch 2.12.0+rocm7.14.0 from the same index (verified clean; stack-switch
is your call: docs/phase4-stack-switch-decision.md).

**A different Radeon (not 7900 XTX)**
`.\quickstart.ps1 -Mode Fast -AllowUntestedGpu` — then please file a GPU
compatibility report with the printed timings.

"""Static safety contracts for the PowerShell entry points (review P0-3).

The behavioral proof lives on the Windows bench host (fake-listener test,
see docs/release-audit/FINAL_AUDIT.md); these source-level contracts keep
CI (any OS) failing loudly if someone reintroduces name-based process
ownership or unconditional port killing.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUICKSTART = (REPO / "quickstart.ps1").read_text(encoding="utf-8")
RUN_VARIANT = (REPO / "bench" / "run_variant.ps1").read_text(encoding="utf-8")
PORTOPS = (REPO / "bench" / "portops.ps1").read_text(encoding="utf-8")
ALL = {"quickstart.ps1": QUICKSTART, "bench/run_variant.ps1": RUN_VARIANT,
       "bench/portops.ps1": PORTOPS}


def test_no_name_based_ownership_anywhere():
    """Ownership must be PID-tree based; 'phase2-comfyui' command-line
    matching was removed because two checkouts share that path fragment."""
    for name, src in ALL.items():
        assert "CommandLine" not in src, f"{name} still inspects command lines"
        assert "-match \"phase2" not in src, name


def test_no_unconditional_port_kill():
    for name, src in ALL.items():
        assert "Kill-Port" not in src, name
        assert "Kill-OwnOrphans" not in src, name
    # outside portops, taskkill may appear ONLY as printed advice for the
    # user (Write-Host) — all actual kills delegate to Stop-OwnTree
    for name, src in (("quickstart.ps1", QUICKSTART), ("bench/run_variant.ps1", RUN_VARIANT)):
        for line in src.splitlines():
            if "taskkill" in line and "Stop-OwnTree" not in line:
                assert "Write-Host" in line, \
                    f"{name} must delegate kills to Stop-OwnTree: {line.strip()}"


def test_portops_has_the_own_tree_helpers():
    for fn in ("function Select-ServerPort", "function Get-DescendantPids",
               "function Stop-OwnTree", "function Test-PortBusy"):
        assert fn in PORTOPS
    assert "Get-CimInstance Win32_Process -Filter \"ParentProcessId=" in PORTOPS


def test_scripts_use_the_helpers_and_fall_forward():
    for name, src in (("quickstart.ps1", QUICKSTART), ("bench/run_variant.ps1", RUN_VARIANT)):
        assert "Select-ServerPort" in src, name
        assert "Get-DescendantPids" in src, name
        assert "Stop-OwnTree" in src, name
        assert ". (Join-Path" in src or ". " in src  # dot-sources portops


def test_keepserver_honored_on_every_exit_path():
    # Fail() only tears down when -KeepServer was NOT given
    assert "if (-not $KeepServer -and $script:ServerProc" in QUICKSTART
    assert "taskkill /PID $($server.Id) /T /F" in QUICKSTART  # printed for manual stop


def test_quickstart_results_are_isolated_from_the_worktree():
    assert "bench\\results\\quickstart" in QUICKSTART
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "bench/results/quickstart/" in ignore


def test_run_variant_refuses_to_clobber_existing_records():
    assert "OverwriteResults" in RUN_VARIANT
    assert "use a new -Date or pass -OverwriteResults" in RUN_VARIANT


def test_comfy_commit_drift_fails_closed():
    assert "AllowComfyCommitDrift" in QUICKSTART
    assert "ComfyUI commit mismatch (fail closed)" in QUICKSTART
    assert "stack_verified" in QUICKSTART  # drift run is recorded unverified
    # -SkipSetup still verifies the stack
    assert "STACK VERIFICATION (always, incl. -SkipSetup" in QUICKSTART


def test_cold_start_vocabulary_is_unified():
    for label in ("Server boot", "Ready-to-first-image", "Full cold start",
                  "Warm (same prompt"):
        assert label in QUICKSTART, label

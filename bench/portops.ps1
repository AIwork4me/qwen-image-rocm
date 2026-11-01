# Shared port & process-ownership helpers for quickstart.ps1 and
# bench/run_variant.ps1 (dot-source: `. $repo\bench\portops.ps1`).
#
# Ownership model (release-review P0-3):
#   - NEVER terminate a process this invocation did not start. Command-line
#     string matching is NOT proof of ownership (two checkouts of this repo
#     share "phase2-comfyui" path fragments and would kill each other), so
#     it is not used anywhere in these helpers.
#   - Startup: if the requested port is busy — by ANYONE — fall forward to a
#     free port. Existing listeners are left untouched.
#   - Teardown: kill exactly the process tree rooted at the PID we started
#     (Start-Process -PassThru). Descendants are enumerated by PPID chain
#     while the root is alive and remembered, so an orphaned child that
#     outlives its root can still be identified as OURS by PID — not by name.
#     Anything else still listening on our port afterwards is reported and
#     left alone.

function Test-PortBusy([int]$p) {
    [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}

function Select-ServerPort([int]$RequestedPort, [int]$MaxOffset = 20) {
    <# Returns the first free port in RequestedPort..RequestedPort+MaxOffset.
       Writes progress/warnings; returns -1 when none free (caller fails). #>
    $p = $RequestedPort
    while ($p -le ($RequestedPort + $MaxOffset)) {
        if (-not (Test-PortBusy $p)) {
            if ($p -ne $RequestedPort) {
                Write-Warning "port $RequestedPort is in use (existing listener left untouched) - using $p"
            }
            return $p
        }
        $p++
    }
    Write-Warning "no free port in $RequestedPort..$($RequestedPort + $MaxOffset)"
    return -1
}

function Get-DescendantPids([int]$RootPid) {
    <# All live descendant PIDs of RootPid (PPID chain, BFS). #>
    $found = @()
    $frontier = @($RootPid)
    while ($frontier.Count -gt 0) {
        $next = @()
        foreach ($pp in $frontier) {
            $kids = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$pp" -ErrorAction SilentlyContinue)
            foreach ($k in $kids) {
                $next += [int]$k.ProcessId
                $found += [int]$k.ProcessId
            }
        }
        $frontier = $next
    }
    return @($found | Select-Object -Unique)
}

function Stop-OwnTree([int]$RootPid, [int[]]$KnownDescendants = @(), [int]$Port = 0) {
    <# Kill ONLY what this run started: the root tree, plus remembered
       descendants if the root already died. Never touches unknown PIDs;
       a stranger left on our port is REPORTED, not killed. #>
    $own = @($RootPid) + @($KnownDescendants | Where-Object { $_ -gt 0 })
    $root = Get-Process -Id $RootPid -ErrorAction SilentlyContinue
    if ($root) {
        Write-Host "stopping own server tree (root PID $RootPid)"
        taskkill /PID $RootPid /T /F 2>$null | Out-Null
    }
    Start-Sleep 2
    # orphaned children of ours (root died before taskkill could tree-kill)
    foreach ($pid2 in ($KnownDescendants | Where-Object { $_ -gt 0 })) {
        if (Get-Process -Id $pid2 -ErrorAction SilentlyContinue) {
            Write-Host "stopping own orphaned child PID $pid2"
            taskkill /PID $pid2 /T /F 2>$null | Out-Null
        }
    }
    if ($Port -gt 0) {
        Start-Sleep 1
        if (Test-PortBusy $Port) {
            $owners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object { $_.OwningProcess } | Select-Object -Unique)
            $foreign = @($owners | Where-Object { $own -notcontains [int]$_ })
            if ($foreign.Count -gt 0) {
                Write-Warning "port $Port still held by PID(s) $($foreign -join ',') - NOT started by this run; leaving them alone (stop manually if they are yours)"
            }
        }
    }
}
